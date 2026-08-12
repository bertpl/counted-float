import builtins

import pytest

from counted_float._core import cli_main
from counted_float._core.compatibility import Capability
from tests._capabilities import needs


@needs(Capability.CLI)
def test_main_runs_cli_when_click_available(monkeypatch):
    # --- arrange -----------------------------------------
    called = []
    from counted_float._core import cli

    monkeypatch.setattr(cli, "cli", lambda: called.append(True))

    # --- act ---------------------------------------------
    cli_main.main()

    # --- assert ------------------------------------------
    assert called == [True]


def test_main_exits_with_guidance_when_the_extra_is_not_installed(monkeypatch, capsys):
    # a capability is absent when its distribution is not installed, which is what gets simulated
    # here -- blocking the import would not make the extra absent, only broken
    # --- arrange -----------------------------------------
    monkeypatch.setattr(Capability, "is_available", lambda _: False)

    # --- act & assert ------------------------------------
    with pytest.raises(SystemExit) as exc_info:
        cli_main.main()

    assert exc_info.value.code == 1
    assert 'pip install "counted-float[cli]"' in capsys.readouterr().err


def test_main_lets_a_genuine_import_failure_surface_as_itself(monkeypatch):
    # with the extra installed, a failure while loading the CLI module is a bug rather than a
    # packaging problem, and must not be dressed up as one
    # --- arrange -----------------------------------------
    monkeypatch.setattr(Capability, "is_available", lambda _: True)
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "counted_float._core.cli":
            raise ModuleNotFoundError("simulated missing dependency", name="something_else")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    # --- act & assert ------------------------------------
    with pytest.raises(ModuleNotFoundError, match="simulated missing dependency"):
        cli_main.main()
