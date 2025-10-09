import click

from counted_float import BuiltInData
from counted_float._core.benchmarking import run_counted_float_benchmark, run_flops_benchmark


# -------------------------------------------------------------------------
#  Commands
# -------------------------------------------------------------------------
@click.group()
def cli():
    pass


@cli.command(short_help="run flop benchmarks")
def benchmark():
    result = run_flops_benchmark()
    result.show()


@cli.command(short_help="show all built-in data")
@click.option("--key_filter", default="", help="Optional key filter for built-in data")
def show_data(key_filter: str):
    BuiltInData.show(key_filter=key_filter)


@cli.command(short_help="run benchmark of float vs CountedFloat performance")
def benchmark_counted_float():
    result = run_counted_float_benchmark()
    result.show()
