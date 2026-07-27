import builtins

import pytest

import counted_float._core.compatibility._optional_dependencies as optional_dependencies
from counted_float._core import _cli_main
from counted_float._core.compatibility import CAP_CLI
from tests._capabilities import needs


@needs(CAP_CLI)
def test_main_runs_cli_when_click_available(monkeypatch):
    # --- arrange -----------------------------------------
    called = []
    from counted_float._core import _cli

    monkeypatch.setattr(_cli, "cli", lambda: called.append(True))

    # --- act ---------------------------------------------
    _cli_main.main()

    # --- assert ------------------------------------------
    assert called == [True]


def test_main_exits_with_guidance_when_the_extra_is_not_installed(monkeypatch, capsys):
    # a capability is absent when its distribution is not installed, which is what gets simulated
    # here -- blocking the import would not make the extra absent, only broken
    # --- arrange -----------------------------------------
    monkeypatch.setattr(optional_dependencies, "is_available", lambda _: False)

    # --- act & assert ------------------------------------
    with pytest.raises(SystemExit) as exc_info:
        _cli_main.main()

    assert exc_info.value.code == 1
    assert 'pip install "counted-float[cli]"' in capsys.readouterr().err


def test_main_lets_a_genuine_import_failure_surface_as_itself(monkeypatch):
    # with the extra installed, a failure while loading the CLI module is a bug rather than a
    # packaging problem, and must not be dressed up as one
    # --- arrange -----------------------------------------
    monkeypatch.setattr(optional_dependencies, "is_available", lambda _: True)
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "counted_float._core._cli":
            raise ModuleNotFoundError("simulated missing dependency", name="something_else")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    # --- act & assert ------------------------------------
    with pytest.raises(ModuleNotFoundError, match="simulated missing dependency"):
        _cli_main.main()
