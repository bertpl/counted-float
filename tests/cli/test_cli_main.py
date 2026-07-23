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


def test_main_reraises_a_non_click_import_error(monkeypatch):
    # only a missing `click` becomes install guidance; any other ModuleNotFoundError propagates
    # --- arrange -----------------------------------------
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "counted_float._core._cli":
            raise ModuleNotFoundError("simulated missing dependency", name="numpy")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    # --- act & assert ------------------------------------
    with pytest.raises(ModuleNotFoundError, match="simulated missing dependency"):
        _cli_main.main()
