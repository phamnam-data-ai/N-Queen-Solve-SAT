"""Isolated, repeatable benchmark execution and result aggregation."""

from .metrics import summarise_results
from .runner import DEFAULT_N_VALUES, PRESETS, BenchmarkRunner, ExperimentSpec

__all__ = ["BenchmarkRunner", "DEFAULT_N_VALUES", "ExperimentSpec", "PRESETS", "summarise_results"]
