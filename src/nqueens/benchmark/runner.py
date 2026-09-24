"""Cross-platform, process-isolated N-Queens experiment runner."""

from __future__ import annotations

import csv
import importlib.metadata
import json
import multiprocessing as mp
import platform
import queue
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Any

import psutil

from ..problem import NQueensResult
from .metrics import summarise_results
from .report import update_report_outline

DEFAULT_N_VALUES = [4, 8, 10, 20, 30, 40, 50, 75, 100, 150, 200]
PRESETS = {
    "small": [4, 8, 10, 20],
    "medium": [25, 50, 75, 100],
    "large": [150, 200, 300, 500],
}
RAW_COLUMNS = [
    "timestamp", "n", "method", "encoding", "backend", "repeat", "status",
    "build_time_sec", "solve_time_sec", "total_time_sec", "num_variables", "num_clauses",
    "num_constraints", "solution_valid", "error_message",
]


@dataclass(frozen=True)
class ExperimentSpec:
    """One independently timed execution sent to a child process."""

    n: int
    method: str
    encoding: str | None
    backend: str
    repeat: int
    timeout_sec: float
    commander_group_size: int = 3
    product_dimension: int | None = None


def _solve_specification(spec: ExperimentSpec) -> NQueensResult:
    """Construct a fresh solver in the worker process and execute it once."""
    if spec.method == "sat":
        from ..sat.solver import SATNQueensSolver

        solver: Any = SATNQueensSolver(
            spec.n,
            encoding=spec.encoding or "sequential",
            sat_solver=spec.backend,
            commander_group_size=spec.commander_group_size,
            product_dimension=spec.product_dimension,
        )
    elif spec.method == "cpsat":
        from ..cpsat.solver import CPSATNQueensSolver

        solver = CPSATNQueensSolver(spec.n, time_limit_sec=spec.timeout_sec)
    elif spec.method == "gurobi":
        from ..mip.gurobi_solver import GurobiNQueensSolver

        solver = GurobiNQueensSolver(spec.n, time_limit_sec=spec.timeout_sec)
    elif spec.method == "cplex-mip":
        from ..mip.cplex_solver import CplexMIPNQueensSolver

        solver = CplexMIPNQueensSolver(spec.n, time_limit_sec=spec.timeout_sec)
    elif spec.method == "cplex-cp":
        from ..cp.cplex_cp_solver import CplexCPNQueensSolver

        solver = CplexCPNQueensSolver(spec.n, time_limit_sec=spec.timeout_sec)
    else:
        raise ValueError(f"unknown benchmark method: {spec.method}")
    try:
        return solver.solve()
    finally:
        close = getattr(solver, "close", None)
        if close is not None:
            close()


def _worker(spec: ExperimentSpec, output: mp.Queue[dict[str, Any]]) -> None:
    """Top-level process target required by Windows' spawn start method."""
    try:
        output.put({"result": _solve_specification(spec).to_dict()})
    except Exception as error:
        output.put({"error": f"worker failed: {type(error).__name__}: {error}"})


def run_experiment(spec: ExperimentSpec) -> dict[str, Any]:
    """Run one experiment in a killable child process and enforce wall timeout."""
    context = mp.get_context("spawn")
    output: mp.Queue[dict[str, Any]] = context.Queue(maxsize=1)
    process = context.Process(target=_worker, args=(spec, output), daemon=True)
    started = perf_counter()
    process.start()
    process.join(spec.timeout_sec)
    elapsed = perf_counter() - started
    if process.is_alive():
        process.terminate()
        process.join()
        output.close()
        return {
            "n": spec.n, "method": spec.method, "encoding": spec.encoding or "",
            "backend": spec.backend, "repeat": spec.repeat, "status": "TIMEOUT",
            "build_time_sec": None, "solve_time_sec": None, "total_time_sec": elapsed,
            "num_variables": None, "num_clauses": None, "num_constraints": None,
            "solution_valid": None, "error_message": f"wall-clock timeout after {spec.timeout_sec} seconds",
        }
    try:
        message = output.get(timeout=2)
    except queue.Empty:
        message = {"error": "worker exited without returning a result"}
    finally:
        output.close()
    if "error" in message:
        return {
            "n": spec.n, "method": spec.method, "encoding": spec.encoding or "",
            "backend": spec.backend, "repeat": spec.repeat, "status": "ERROR",
            "build_time_sec": None, "solve_time_sec": None, "total_time_sec": elapsed,
            "num_variables": None, "num_clauses": None, "num_constraints": None,
            "solution_valid": None, "error_message": message["error"],
        }
    result = message["result"]
    result.update({"encoding": result.get("encoding") or "", "repeat": spec.repeat})
    return result


def _package_version(package: str) -> str | None:
    try:
        return importlib.metadata.version(package)
    except importlib.metadata.PackageNotFoundError:
        return None


def write_environment(path: Path, configuration: dict[str, Any]) -> None:
    """Capture execution environment without including import or plotting time."""
    memory = psutil.virtual_memory()
    payload = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu": platform.processor() or platform.machine(),
        "physical_cpu_count": psutil.cpu_count(logical=False),
        "logical_cpu_count": psutil.cpu_count(logical=True),
        "ram_bytes": memory.total,
        "package_versions": {
            package: _package_version(package)
            for package in ("python-sat", "ortools", "numpy", "pandas", "matplotlib", "psutil", "gurobipy", "docplex", "cplex")
        },
        "benchmark_configuration": configuration,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class BenchmarkRunner:
    """Appendable benchmark runner that preserves raw observations for audit."""

    def __init__(self, results_dir: Path) -> None:
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.raw_csv = self.results_dir / "raw_results.csv"
        self.summary_csv = self.results_dir / "summary_results.csv"

    def _completed_keys(self) -> set[tuple[str, ...]]:
        if not self.raw_csv.exists():
            return set()
        with self.raw_csv.open(newline="", encoding="utf-8") as file:
            return {
                (row["n"], row["method"], row["encoding"], row["backend"], row["repeat"])
                for row in csv.DictReader(file)
            }

    @staticmethod
    def _key(spec: ExperimentSpec) -> tuple[str, ...]:
        return (str(spec.n), spec.method, spec.encoding or "", spec.backend, str(spec.repeat))

    def _append(self, record: dict[str, Any]) -> None:
        new_file = not self.raw_csv.exists()
        record = {**{column: None for column in RAW_COLUMNS}, **record}
        record["timestamp"] = datetime.now(timezone.utc).isoformat()
        with self.raw_csv.open("a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=RAW_COLUMNS)
            if new_file:
                writer.writeheader()
            writer.writerow({column: record[column] for column in RAW_COLUMNS})

    def run(
        self,
        *,
        n_values: list[int],
        methods: list[str],
        sat_encodings: list[str],
        repeats: int,
        timeout_sec: float,
        sat_backend: str = "glucose3",
        resume: bool = False,
        warmup: bool = True,
        commander_group_size: int = 3,
        product_dimension: int | None = None,
    ) -> list[dict[str, Any]]:
        """Execute requested combinations, append raw CSV, then write summary."""
        if repeats < 1 or timeout_sec <= 0:
            raise ValueError("repeats and timeout_sec must be positive")
        known_methods = {"sat", "cpsat", "gurobi", "cplex-mip", "cplex-cp"}
        unknown = set(methods) - known_methods
        if unknown:
            raise ValueError(f"unknown methods: {', '.join(sorted(unknown))}")
        existing = self._completed_keys() if resume else set()
        configuration = {
            "n_values": n_values, "methods": methods, "sat_encodings": sat_encodings,
            "repeats": repeats, "timeout_sec": timeout_sec, "sat_backend": sat_backend,
            "warmup": warmup, "commander_group_size": commander_group_size,
            "product_dimension": product_dimension,
        }
        write_environment(self.results_dir / "environment.json", configuration)
        project_root = Path(__file__).resolve().parents[3]
        update_report_outline(self.results_dir / "environment.json", project_root / "docs" / "report_outline.md")

        specs: list[ExperimentSpec] = []
        for n in n_values:
            for method in methods:
                encodings = sat_encodings if method == "sat" else [None]
                backend = sat_backend if method == "sat" else {
                    "cpsat": "ortools-cp-sat", "gurobi": "gurobi", "cplex-mip": "cplex-mip", "cplex-cp": "cplex-cp",
                }[method]
                for encoding in encodings:
                    for repeat in range(1, repeats + 1):
                        spec = ExperimentSpec(n, method, encoding, backend, repeat, timeout_sec, commander_group_size, product_dimension)
                        if not (resume and self._key(spec) in existing):
                            specs.append(spec)

        if warmup and specs:
            sample = specs[0]
            warmup_spec = ExperimentSpec(4, sample.method, sample.encoding, sample.backend, 0, min(timeout_sec, 10), commander_group_size, product_dimension)
            run_experiment(warmup_spec)  # intentionally not recorded

        records: list[dict[str, Any]] = []
        for spec in specs:
            record = run_experiment(spec)
            self._append(record)
            records.append(record)
        summarise_results(self.raw_csv, self.summary_csv)
        return records
