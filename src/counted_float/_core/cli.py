from pathlib import Path

import click

from counted_float import BuiltInData
from counted_float._core.benchmarking import run_flops_benchmark
from counted_float._core.evaluation import evaluate_counting_overhead


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
    # a first-time reader can mistake these weights for absolute truth; the one-line footer names
    # them as model-relative and points at the cost model rather than restating its caveats here
    click.echo(
        "Weights are model-relative estimates (relative to ADD); see the cost model for the "
        "pricing rules and their caveats: https://counted-float.readthedocs.io/en/latest/cost_model/"
    )


@cli.command(short_help="evaluate the counting overhead of CountedFloat vs float")
def evaluate_overhead() -> None:
    result = evaluate_counting_overhead()
    result.show()


# `benchmark` is what the flops suite does to a machine; this measures the library, so it is named
# for evaluation instead. Hidden rather than listed: the alias is for install strings already in
# use, not something a new reader should discover and pick.
@cli.command(name="benchmark-counted-float", hidden=True)
@click.pass_context
def benchmark_counted_float(ctx: click.Context) -> None:
    click.echo(
        "'benchmark-counted-float' is deprecated and will be removed in the next major version; "
        "use 'evaluate-overhead' instead.",
        err=True,
    )
    ctx.invoke(evaluate_overhead)
