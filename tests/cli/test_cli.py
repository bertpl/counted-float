from pathlib import Path

import pytest
from click.testing import CliRunner

from counted_float import BuiltInData
from counted_float._core import _cli
from counted_float._core._cli import benchmark, benchmark_counted_float, show_data
from counted_float._core.models import FlopsBenchmarkResults


def test_show_data():
    runner = CliRunner()
    runner.invoke(show_data)


@pytest.mark.parametrize("flag", ["--key-filter", "--key_filter"])
def test_show_data_key_filter_spellings(flag: str, monkeypatch) -> None:
    """Both the kebab-case flag and its underscore alias forward the same filter value."""

    # --- arrange ----------------------
    seen: list[str] = []
    monkeypatch.setattr(BuiltInData, "show", classmethod(lambda cls, key_filter="": seen.append(key_filter)))

    # --- act --------------------------
    result = CliRunner().invoke(show_data, [flag, "arm"])

    # --- assert -----------------------
    assert result.exit_code == 0
    assert seen == ["arm"]


def test_benchmark_counted_float():
    runner = CliRunner()
    runner.invoke(benchmark_counted_float)


def test_benchmark_output_round_trip(tmp_path: Path, monkeypatch):
    """`benchmark --output` writes JSON that loads back through the built-in-data path unchanged."""

    # --- arrange -----------------------------------------
    # patch out the actual benchmark run (slow) with a realistic built-in result
    results = list(BuiltInData.benchmarks().values()).pop()
    monkeypatch.setattr(_cli, "run_flops_benchmark", lambda: results)
    output_path = tmp_path / "benchmark_results.json"

    # --- act ---------------------------------------------
    result = CliRunner().invoke(benchmark, ["--output", str(output_path)])

    # --- assert ------------------------------------------
    assert result.exit_code == 0
    round_tripped = FlopsBenchmarkResults.model_validate_json(output_path.read_text(encoding="utf-8"))
    assert round_tripped == results
