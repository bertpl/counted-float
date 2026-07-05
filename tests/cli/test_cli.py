from click.testing import CliRunner

from counted_float._core._cli import benchmark_counted_float, show_data


def test_show_data():
    runner = CliRunner()
    runner.invoke(show_data)


def test_benchmark_counted_float():
    runner = CliRunner()
    runner.invoke(benchmark_counted_float)
