from click.testing import CliRunner

from counted_float._core._cli import benchmark_counted_float, cli, show_data


def test_show_data():
    runner = CliRunner()
    result = runner.invoke(show_data)


def test_benchmark_counted_float():
    runner = CliRunner()
    result = runner.invoke(benchmark_counted_float)
