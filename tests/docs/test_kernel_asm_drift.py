"""The committed kernel ASM listings must stay in step with what the kernels compile to.

Counterpart of the docs-content drift test, for the machine-code listings under docs/kernel_asm/:
the generator recompiles the kernels and this test fails on any difference with the committed
listings. Unlike that test, this one can only run where the listings were generated — the pages
are committed as ARM64 machine code and need numba to compile — so it skips everywhere else and
guards the listings on the regen machine rather than in CI.
"""

import platform
import subprocess
import sys
from pathlib import Path

import pytest

from counted_float._core.compatibility import is_numba_installed

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATOR = REPO_ROOT / "scripts" / "generate_kernel_asm_docs.py"


@pytest.mark.skipif(
    platform.machine() != "arm64" or not is_numba_installed(),
    reason="listings are ARM64 machine code and need numba to regenerate",
)
def test_kernel_asm_listings_match_committed_content():
    """Fails when a kernel compiles differently and `make regen-kernel-asm` was not re-run."""
    # --- act ---------------------------------------------
    result = subprocess.run(  # noqa: S603 -- fixed, repo-local command
        [sys.executable, str(GENERATOR), "--check"],
        capture_output=True,
        encoding="utf-8",
        cwd=REPO_ROOT,
        check=False,  # the return code is the assertion
    )

    # --- assert ------------------------------------------
    assert result.returncode == 0, f"stale kernel ASM listings:\n{result.stderr}"
