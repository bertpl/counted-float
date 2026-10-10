"""Guards for the CI-matrix coverage check (scripts/check_python_matrix.py)."""

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "check_python_matrix.py"


def _load_module():
    """Import the check by path -- scripts/ is maintainer tooling, not an importable package."""
    spec = importlib.util.spec_from_file_location("check_python_matrix", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_mod = _load_module()


def test_reads_only_quoted_matrix_python_values(tmp_path):
    """The parser picks up quoted `python:` matrix legs and ignores every `python_version:` key."""
    # --- arrange ----------------------
    workflow = tmp_path / "wf.yml"
    workflow.write_text(
        "        include:\n"
        '          - { os: ubuntu-latest, python: "3.11", resolution: highest }\n'
        '          - { os: ubuntu-latest, python: "3.14t", resolution: highest }\n'
        "          python_version: ${{ matrix.python }}\n"
        '          python_version: "3.15"\n',
        encoding="utf-8",
    )

    # --- act --------------------------
    tested = _mod.read_tested_versions(workflow)

    # --- assert -----------------------
    assert tested == {"3.11", "3.14t"}


@pytest.mark.parametrize(
    ("declared", "tested", "expected_exit_code"),
    [
        ({"3.11", "3.15"}, {"3.11", "3.14t"}, 1),  # 3.15 has no matrix leg
        ({"3.11"}, {"3.11", "3.14t"}, 0),  # an extra matrix leg is fine
    ],
)
def test_main_fails_only_on_a_declared_version_without_a_leg(monkeypatch, declared, tested, expected_exit_code):
    """The check fails on a declared version that has no matrix leg, and accepts extra matrix legs."""
    # --- arrange ----------------------
    monkeypatch.setattr(_mod, "read_declared_versions", lambda: declared)
    monkeypatch.setattr(_mod, "read_tested_versions", lambda: tested)

    # --- act --------------------------
    exit_code = _mod.main()

    # --- assert -----------------------
    assert exit_code == expected_exit_code


def test_repo_matrix_covers_declared_versions():
    """The live repo satisfies the invariant: every declared version has a matrix leg."""
    # --- act / assert -----------------
    assert _mod.main() == 0
