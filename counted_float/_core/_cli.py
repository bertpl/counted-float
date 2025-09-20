import click

from counted_float import BuiltInData
from counted_float.benchmarking import run_flops_benchmark


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
def show_data():
    BuiltInData.show()
