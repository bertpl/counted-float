"""Compute release metrics from the combined CI coverage data.

Run by the coverage-combine job after ``coverage combine``, with the combined
``.coverage`` present in the working directory. Writes a metrics JSON (path from
``argv[1]``) with the numbers the release stamps into the README badges:
``coverage_pct`` (combined matrix total) and ``test_count`` (collected tests).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _coverage_total() -> float:
    """Return the combined coverage percentage from the current ``.coverage``."""
    # --fail-under=0: just read the number; the gate is enforced by the combine job's report step
    out = subprocess.run(
        [sys.executable, "-m", "coverage", "report", "--format=total", "--fail-under=0"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return float(out.strip())


def _test_count() -> int:
    """Return the number of collected tests (``pytest --collect-only`` node-ids).

    Counts in a single environment (one Python, no extras), so the number is
    accurate only while the suite collects uniformly across the matrix; a
    conditionally-collected test would skew it.
    """
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "./tests", "--collect-only", "-q"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return sum(1 for line in out.splitlines() if "::" in line)


def main() -> None:
    """Compute metrics and write them to the JSON path in ``argv[1]``."""
    out_path = Path(sys.argv[1])
    metrics = {"coverage_pct": _coverage_total(), "test_count": _test_count()}
    print(json.dumps(metrics, indent=2))
    out_path.write_text(json.dumps(metrics, indent=2) + "\n")


if __name__ == "__main__":
    main()
