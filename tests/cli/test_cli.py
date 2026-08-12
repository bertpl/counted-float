from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from counted_float import BuiltInData
from counted_float._core import cli
from counted_float._core.cli import benchmark, benchmark_counted_float, evaluate_overhead, show_data
from counted_float._core.models import FlopsBenchmarkResults


def test_show_data():
    runner = CliRunner()
    runner.invoke(show_data)


def test_show_data_prints_model_relative_footer():
    """`show-data` closes with a caveat naming the weights as model-relative and linking the docs."""
    result = CliRunner().invoke(show_data)
    assert result.exit_code == 0
    assert "model-relative" in result.output
    assert "counted-float.readthedocs.io/en/latest/cost_model/" in result.output


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


def test_evaluate_overhead_invokes_the_evaluation(monkeypatch):
    """`evaluate-overhead` runs the counting-overhead evaluation and shows its result."""

    # --- arrange -----------------------------------------
    # replace the real (slow) evaluation with a fast fake, and prove the command actually calls it
    calls: list[bool] = []

    class _FakeResult:
        def show(self) -> None:
            click.echo("fake evaluation shown")

    def _fake_evaluation() -> _FakeResult:
        calls.append(True)
        return _FakeResult()

    monkeypatch.setattr(cli, "evaluate_counting_overhead", _fake_evaluation)

    # --- act ---------------------------------------------
    result = CliRunner().invoke(evaluate_overhead)

    # --- assert ------------------------------------------
    assert result.exit_code == 0
    assert calls == [True]  # the command invoked the (patched) evaluation exactly once
    assert "fake evaluation shown" in result.output  # and rendered its result via .show()


def test_the_old_command_name_still_runs_and_warns(monkeypatch):
    """`benchmark-counted-float` still does the work, but says what to move to."""

    # --- arrange -----------------------------------------
    class _FakeResult:
        def show(self) -> None:
            click.echo("fake evaluation shown")

    def _fake_evaluation() -> _FakeResult:
        return _FakeResult()

    monkeypatch.setattr(cli, "evaluate_counting_overhead", _fake_evaluation)

    # --- act ---------------------------------------------
    result = CliRunner().invoke(benchmark_counted_float)

    # --- assert ------------------------------------------
    assert result.exit_code == 0
    assert "fake evaluation shown" in result.output  # the alias still does the work
    assert "deprecated" in result.output
    assert "evaluate-overhead" in result.output  # and names its replacement


def test_the_old_command_name_is_hidden_from_help():
    """The alias exists for install strings already in use, not for new readers to discover."""
    result = CliRunner().invoke(cli.cli, ["--help"])
    assert result.exit_code == 0
    assert "evaluate-overhead" in result.output
    assert "benchmark-counted-float" not in result.output


def test_benchmark_output_round_trip(tmp_path: Path, monkeypatch):
    """`benchmark --output` writes JSON that loads back through the built-in-data path unchanged."""

    # --- arrange -----------------------------------------
    # patch out the actual benchmark run (slow) with a realistic built-in result
    results = list(BuiltInData.benchmarks().values()).pop()
    monkeypatch.setattr(cli, "run_flops_benchmark", lambda: results)
    output_path = tmp_path / "benchmark_results.json"

    # --- act ---------------------------------------------
    result = CliRunner().invoke(benchmark, ["--output", str(output_path)])

    # --- assert ------------------------------------------
    assert result.exit_code == 0
    round_tripped = FlopsBenchmarkResults.model_validate_json(output_path.read_text(encoding="utf-8"))
    assert round_tripped == results


def test_benchmark_echoes_the_output_path(tmp_path: Path, monkeypatch):
    """`benchmark --output` confirms the write with a 'Results written to' line naming the path."""

    # --- arrange -----------------------------------------
    results = list(BuiltInData.benchmarks().values()).pop()
    monkeypatch.setattr(cli, "run_flops_benchmark", lambda: results)
    output_path = tmp_path / "benchmark_results.json"

    # --- act ---------------------------------------------
    result = CliRunner().invoke(benchmark, ["--output", str(output_path)])

    # --- assert ------------------------------------------
    assert result.exit_code == 0
    assert f"Results written to '{output_path}'." in result.output


def test_benchmark_without_output_writes_nothing_and_stays_silent(monkeypatch):
    """With no --output the command shows results but skips the file write and its confirmation."""

    # --- arrange -----------------------------------------
    results = list(BuiltInData.benchmarks().values()).pop()
    monkeypatch.setattr(cli, "run_flops_benchmark", lambda: results)

    # --- act ---------------------------------------------
    result = CliRunner().invoke(benchmark)

    # --- assert ------------------------------------------
    assert result.exit_code == 0
    assert "Results written to" not in result.output  # no write happened, so no confirmation line
