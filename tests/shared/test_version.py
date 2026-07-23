"""The package __version__ fallback when installed metadata is unavailable (source-tree use)."""

import importlib
import importlib.metadata

import counted_float


def test_version_falls_back_when_package_metadata_is_missing(monkeypatch):
    # a source tree without installed metadata makes importlib.metadata.version raise; __init__
    # must fall back to "0.0.0" rather than letting PackageNotFoundError escape at import
    # --- arrange -----------------------------------------
    def _raise_not_found(_name):
        raise importlib.metadata.PackageNotFoundError

    monkeypatch.setattr(importlib.metadata, "version", _raise_not_found)

    # --- act ---------------------------------------------
    try:
        importlib.reload(counted_float)
        fallback_version = counted_float.__version__
    finally:
        monkeypatch.undo()
        importlib.reload(counted_float)  # restore the real __version__ for later tests

    # --- assert ------------------------------------------
    assert fallback_version == "0.0.0"
