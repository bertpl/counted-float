import builtins

import pytest

from counted_float._core import _cli_main


def test_main_runs_cli_when_click_available(monkeypatch):
    # --- arrange -----------------------------------------
    called = []
    from counted_float._core import _cli

    monkeypatch.setattr(_cli, "cli", lambda: called.append(True))

    # --- act ---------------------------------------------
    _cli_main.main()

    # --- assert ------------------------------------------
    assert called == [True]


def test_main_exits_with_guidance_when_click_missing(monkeypatch, capsys):
    # --- arrange -----------------------------------------
    # simulate a base install: importing the click-based CLI module raises for `click`
    monkeypatch.delitem(__import__("sys").modules, "counted_float._core._cli", raising=False)
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "click":
            raise ModuleNotFoundError("No module named 'click'", name="click")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    # --- act & assert ------------------------------------
    with pytest.raises(SystemExit) as exc_info:
        _cli_main.main()
    assert exc_info.value.code == 1
    assert 'pip install "counted-float[cli]"' in capsys.readouterr().err


def test_main_keeps_the_real_cause_behind_the_guidance(monkeypatch, capsys):
    # any import failure while loading the CLI module is reported as the missing extra -- that is the
    # only thing a user can act on -- but the module that was actually absent stays chained to it, so
    # a genuine bug in there is still diagnosable rather than dressed up as a packaging problem
    # --- arrange -----------------------------------------
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "counted_float._core._cli":
            raise ModuleNotFoundError("simulated missing dependency", name="something_else")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    # --- act & assert ------------------------------------
    with pytest.raises(SystemExit) as exc_info:
        _cli_main.main()

    assert exc_info.value.code == 1
    assert 'pip install "counted-float[cli]"' in capsys.readouterr().err
    assert exc_info.value.__context__.__cause__.name == "something_else"
