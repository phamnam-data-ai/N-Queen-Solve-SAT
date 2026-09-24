"""CSV summary statistics for repeated solver experiments."""

from __future__ import annotations

from pathlib import Path
from typing import Any

SUMMARY_COLUMNS = [
    "n", "method", "encoding", "backend", "status", "runs",
    "solve_time_mean_sec", "solve_time_median_sec", "solve_time_std_sec", "solve_time_min_sec", "solve_time_max_sec",
    "total_time_mean_sec", "total_time_median_sec", "total_time_std_sec", "total_time_min_sec", "total_time_max_sec",
]


def summarise_results(raw_csv: Path, summary_csv: Path) -> Any:
    """Write summary metrics using only runs with independently valid solutions."""
    # Import only after all child-process experiments have completed.  Keeping
    # pandas out of runner module import is important on Windows: spawned
    # workers should load only the solver selected for that experiment.
    import pandas as pd
    if not raw_csv.exists():
        frame = pd.DataFrame(columns=SUMMARY_COLUMNS)
        frame.to_csv(summary_csv, index=False)
        return frame

    raw = pd.read_csv(raw_csv)
    if raw.empty or "solution_valid" not in raw:
        frame = pd.DataFrame(columns=SUMMARY_COLUMNS)
        frame.to_csv(summary_csv, index=False)
        return frame
    valid = raw[raw["solution_valid"].astype(str).str.lower().eq("true")].copy()
    if valid.empty:
        frame = pd.DataFrame(columns=SUMMARY_COLUMNS)
        frame.to_csv(summary_csv, index=False)
        return frame

    grouped = valid.groupby(["n", "method", "encoding", "backend", "status"], dropna=False)
    summary = grouped.agg(
        runs=("repeat", "count"),
        solve_time_mean_sec=("solve_time_sec", "mean"),
        solve_time_median_sec=("solve_time_sec", "median"),
        solve_time_std_sec=("solve_time_sec", "std"),
        solve_time_min_sec=("solve_time_sec", "min"),
        solve_time_max_sec=("solve_time_sec", "max"),
        total_time_mean_sec=("total_time_sec", "mean"),
        total_time_median_sec=("total_time_sec", "median"),
        total_time_std_sec=("total_time_sec", "std"),
        total_time_min_sec=("total_time_sec", "min"),
        total_time_max_sec=("total_time_sec", "max"),
    ).reset_index()
    summary = summary[SUMMARY_COLUMNS].sort_values(["method", "encoding", "n"], na_position="last")
    summary.to_csv(summary_csv, index=False)
    return summary
