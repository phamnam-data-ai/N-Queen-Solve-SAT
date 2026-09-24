"""Refresh only the auto-filled experimental-setup block in the report outline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nqueens.benchmark.report import update_report_outline


def main() -> int:
    parser = argparse.ArgumentParser(description="Populate report setup metadata from environment.json.")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--outline", type=Path, default=ROOT / "docs" / "report_outline.md")
    arguments = parser.parse_args()
    update_report_outline(arguments.results_dir / "environment.json", arguments.outline)
    print(arguments.outline)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
