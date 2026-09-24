"""Publication-friendly charts generated only from measured benchmark CSV rows."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def _valid_rows(raw_csv: Path) -> pd.DataFrame:
    if not raw_csv.exists():
        raise FileNotFoundError(f"raw benchmark file does not exist: {raw_csv}")
    frame = pd.read_csv(raw_csv)
    if frame.empty:
        raise ValueError("raw benchmark CSV contains no rows")
    valid = frame[frame["solution_valid"].astype(str).str.lower().eq("true")].copy()
    if valid.empty:
        raise ValueError("raw benchmark CSV has no valid solved instances to plot")
    for column in ("n", "solve_time_sec", "total_time_sec", "num_clauses", "num_variables"):
        if column in valid:
            valid[column] = pd.to_numeric(valid[column], errors="coerce")
    return valid


def _save_time_plot(data: pd.DataFrame, metric: str, ylabel: str, output: Path, log_scale: bool = False) -> None:
    figure, axis = plt.subplots(figsize=(8.2, 5.2))
    for label, group in data.groupby("label"):
        series = group.groupby("n", as_index=False)[metric].mean().sort_values("n")
        axis.plot(series["n"], series[metric], marker="o", linewidth=1.8, label=label)
    axis.set_title(f"N-Queens: {ylabel} by solving method")
    axis.set_xlabel("Board size N")
    axis.set_ylabel(ylabel + (" (log scale)" if log_scale else " (seconds)"))
    if log_scale:
        axis.set_yscale("log")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _save_sat_size_plot(data: pd.DataFrame, metric: str, ylabel: str, output: Path) -> None:
    sat = data[data["method"].eq("sat") & data[metric].notna()]
    if sat.empty:
        return
    figure, axis = plt.subplots(figsize=(8.2, 5.2))
    for encoding, group in sat.groupby("encoding"):
        series = group.groupby("n", as_index=False)[metric].mean().sort_values("n")
        axis.plot(series["n"], series[metric], marker="o", linewidth=1.8, label=encoding)
    axis.set_title(f"SAT encoding comparison: {ylabel}")
    axis.set_xlabel("Board size N")
    axis.set_ylabel(ylabel)
    axis.grid(True, alpha=0.25)
    axis.legend(title="Encoding")
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)


def _save_encoding_bar(data: pd.DataFrame, output: Path) -> None:
    sat = data[data["method"].eq("sat") & data["solve_time_sec"].notna()]
    if sat.empty or sat["encoding"].nunique() < 2:
        return
    n_value = int(sat["n"].max())
    series = sat[sat["n"].eq(n_value)].groupby("encoding", as_index=False)["solve_time_sec"].mean()
    figure, axis = plt.subplots(figsize=(7.5, 5.0))
    axis.bar(series["encoding"], series["solve_time_sec"], color="#4C78A8")
    axis.set_title(f"SAT encoding solve time at N={n_value}")
    axis.set_xlabel("AMO encoding")
    axis.set_ylabel("Mean solve time (seconds)")
    axis.grid(axis="y", alpha=0.25)
    figure.tight_layout()
    figure.savefig(output, dpi=180)
    plt.close(figure)


def generate_plots(raw_csv: Path, figures_dir: Path) -> list[Path]:
    """Create requested figures from real valid observations and return paths."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    data = _valid_rows(raw_csv)
    data["label"] = data.apply(
        lambda row: f"SAT ({row['encoding']})" if row["method"] == "sat" else str(row["method"]), axis=1
    )
    created: list[Path] = []
    chart_specs = [
        ("solve_time_sec", "Solve time", "solve_time_comparison.png", False),
        ("solve_time_sec", "Solve time", "solve_time_log.png", True),
        ("total_time_sec", "Total time", "total_time_comparison.png", False),
        ("total_time_sec", "Total time", "total_time_log.png", True),
    ]
    for metric, ylabel, name, log_scale in chart_specs:
        positive = data[metric].dropna()
        if not positive.empty and (not log_scale or (positive > 0).all()):
            path = figures_dir / name
            _save_time_plot(data, metric, ylabel, path, log_scale)
            created.append(path)
    sat_time = figures_dir / "sat_encoding_time.png"
    if not data[data["method"].eq("sat")].empty:
        _save_time_plot(data[data["method"].eq("sat")], "solve_time_sec", "SAT solve time", sat_time)
        created.append(sat_time)
    for metric, ylabel, name in (
        ("num_clauses", "Number of CNF clauses", "sat_clause_count.png"),
        ("num_variables", "Number of SAT variables", "sat_variable_count.png"),
    ):
        path = figures_dir / name
        _save_sat_size_plot(data, metric, ylabel, path)
        if path.exists():
            created.append(path)
    bar = figures_dir / "sat_encoding_by_n.png"
    _save_encoding_bar(data, bar)
    if bar.exists():
        created.append(bar)
    return created
