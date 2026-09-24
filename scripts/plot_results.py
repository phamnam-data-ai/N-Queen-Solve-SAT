"""Generate report-ready plots strictly from recorded benchmark observations."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nqueens.benchmark.plots import generate_plots


def main() -> int:
    parser = argparse.ArgumentParser(description="Plot actual N-Queens benchmark results.")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    arguments = parser.parse_args()
    paths = generate_plots(arguments.results_dir / "raw_results.csv", arguments.results_dir / "figures")
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
