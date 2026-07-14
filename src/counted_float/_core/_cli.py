from pathlib import Path

import click

from counted_float import BuiltInData
from counted_float._core.benchmarking import run_counted_float_benchmark, run_flops_benchmark


# -------------------------------------------------------------------------
#  Commands
# -------------------------------------------------------------------------
@click.group()
def cli() -> None:
    pass


@cli.command(short_help="run flop benchmarks")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    default=None,
    help="Optional file path to write results to as JSON, in the same schema as the built-in data files.",
)
def benchmark(output: Path | None) -> None:
    result = run_flops_benchmark()
    result.show()
    if output is not None:
        output.write_text(result.model_dump_json(indent=4) + "\n", encoding="utf-8")
        click.echo(f"Results written to '{output}'.")


@cli.command(short_help="show all built-in data")
@click.option(
    "--key-filter",
    "--key_filter",
    "key_filter",
    default="",
    help="Optional key filter for built-in data",
)
def show_data(key_filter: str) -> None:
    BuiltInData.show(key_filter=key_filter)


@cli.command(short_help="run benchmark of float vs CountedFloat performance")
def benchmark_counted_float() -> None:
    result = run_counted_float_benchmark()
    result.show()
