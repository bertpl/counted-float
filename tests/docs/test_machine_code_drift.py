"""The committed machine-code listings must stay in step with what the probes compile to.

Counterpart of the docs-content drift test, for the machine-code listings under docs/machine_code/:
the generator recompiles the probes and this test fails on any difference with the committed
listings. Unlike that test, this one can only run where the listings were generated — the pages
are committed as ARM64 machine code and need numba to compile — so it skips everywhere else and
guards the listings on the regen machine rather than in CI.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

import pytest

from counted_float._core.compatibility import Capability

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATOR = REPO_ROOT / "scripts" / "generate_machine_code_docs.py"


@pytest.mark.skipif(
    platform.machine() != "arm64"
    or not Capability.FLOPS_BENCHMARKING.is_available()
    or os.environ.get("CI") is not None,
    reason="listings are ARM64 machine code, need numba to regenerate, and are pinned to the "
    "regen machine's toolchain -- CI's macos runners are arm64 too, but their LLVM/numba may "
    "legitimately generate different code",
)
def test_machine_code_listings_match_committed_content():
    """Fails when a probe compiles differently and `make regen-machine-code` was not re-run."""
    # --- act ---------------------------------------------
    result = subprocess.run(  # noqa: S603 -- fixed, repo-local command
        [sys.executable, str(GENERATOR), "--check"],
        capture_output=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
        check=False,  # the return code is the assertion
    )

    # --- assert ------------------------------------------
    assert result.returncode == 0, f"stale machine-code listings:\n{result.stderr}"
