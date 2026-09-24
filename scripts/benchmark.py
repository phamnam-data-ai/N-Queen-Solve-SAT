"""Run repeatable N-Queens benchmark experiments with subprocess timeouts."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nqueens.benchmark.runner import DEFAULT_N_VALUES, PRESETS, BenchmarkRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark N-Queens exact solving methods.")
    parser.add_argument("--n-values", nargs="+", type=int, help="explicit N values")
    parser.add_argument("--preset", choices=sorted(PRESETS), help="small, medium, or large N preset")
    parser.add_argument("--methods", nargs="+", default=["sat", "cpsat"], choices=["sat", "cpsat", "gurobi", "cplex-mip", "cplex-cp", "all"])
    parser.add_argument("--sat-encodings", nargs="+", default=["pairwise", "sequential", "binary", "commander", "product"],
                        choices=["pairwise", "sequential", "binary", "commander", "product"])
    parser.add_argument("--sat-solver", default="glucose3")
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=60.0, help="wall-clock seconds per experiment")
    parser.add_argument("--resume", action="store_true", help="skip combinations already present in raw_results.csv")
    parser.add_argument("--no-warmup", action="store_true")
    parser.add_argument("--commander-group-size", type=int, default=3)
    parser.add_argument("--product-dimension", type=int, default=None)
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    return parser


def main() -> int:
    arguments = build_parser().parse_args()
    n_values = arguments.n_values or (PRESETS[arguments.preset] if arguments.preset else DEFAULT_N_VALUES)
    methods = ["sat", "cpsat", "gurobi", "cplex-mip", "cplex-cp"] if "all" in arguments.methods else arguments.methods
    runner = BenchmarkRunner(arguments.results_dir)
    records = runner.run(
        n_values=n_values, methods=methods, sat_encodings=arguments.sat_encodings,
        repeats=arguments.repeats, timeout_sec=arguments.timeout, sat_backend=arguments.sat_solver,
        resume=arguments.resume, warmup=not arguments.no_warmup,
        commander_group_size=arguments.commander_group_size, product_dimension=arguments.product_dimension,
    )
    counts = Counter(record["status"] for record in records)
    print(f"Recorded {len(records)} experiment(s) in {runner.raw_csv}")
    print("Status counts:", dict(sorted(counts.items())))
    print(f"Summary: {runner.summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
