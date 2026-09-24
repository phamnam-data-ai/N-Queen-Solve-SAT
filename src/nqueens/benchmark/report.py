"""Keep the report-outline setup block synchronized with environment metadata."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

START = "<!-- BEGIN AUTO ENVIRONMENT -->"
END = "<!-- END AUTO ENVIRONMENT -->"


def update_report_outline(environment_path: Path, outline_path: Path) -> None:
    """Replace only the marked setup block with values from environment JSON."""
    if not environment_path.exists() or not outline_path.exists():
        return
    data: dict[str, Any] = json.loads(environment_path.read_text(encoding="utf-8"))
    config = data.get("benchmark_configuration", {})
    versions = data.get("package_versions", {})
    package_text = ", ".join(f"{name}={version or 'unavailable'}" for name, version in versions.items())
    block = "\n".join(
        [
            START,
            "| Item | Measured configuration |",
            "| --- | --- |",
            f"| OS / Python | {data.get('os', 'unknown')} / {data.get('python', 'unknown')} |",
            f"| CPU / RAM | {data.get('cpu', 'unknown')} / {data.get('ram_bytes', 'unknown')} bytes |",
            f"| Packages | {package_text} |",
            f"| N values | {config.get('n_values', [])} |",
            f"| Repetitions | {config.get('repeats', 'unknown')} |",
            f"| Timeout per experiment | {config.get('timeout_sec', 'unknown')} s |",
            f"| Methods / SAT backend | {config.get('methods', [])} / {config.get('sat_backend', 'unknown')} |",
            f"| SAT parameters | encodings={config.get('sat_encodings', [])}; commander group={config.get('commander_group_size', 'unknown')}; product dimension={config.get('product_dimension', None)} |",
            END,
        ]
    )
    text = outline_path.read_text(encoding="utf-8")
    pattern = re.escape(START) + r".*?" + re.escape(END)
    if re.search(pattern, text, flags=re.DOTALL):
        outline_path.write_text(re.sub(pattern, block, text, flags=re.DOTALL), encoding="utf-8")
