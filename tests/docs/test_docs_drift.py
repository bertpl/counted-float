"""The committed docs' generated blocks must stay in step with what the library produces.

Counterpart of the precomputed-weights drift test, for rendered documentation content: the
generator script re-derives every marked text block and this test fails on any difference with
what is committed — so a data or rendering change that forgets `make regen-docs` fails the suite
instead of shipping stale docs. Images are excluded by design: they only regenerate
byte-identically on the machine that rendered them.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GENERATOR = REPO_ROOT / "scripts" / "generate_docs_content.py"


def test_generated_docs_blocks_match_committed_content():
    """Fails when a generated docs block changed and `make regen-docs` was not re-run."""
    # --- act ---------------------------------------------
    result = subprocess.run(  # noqa: S603 -- fixed, repo-local command
        [sys.executable, str(GENERATOR), "--check"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,  # the return code is the assertion
    )

    # --- assert ------------------------------------------
    assert result.returncode == 0, f"stale generated docs content:\n{result.stderr}"
