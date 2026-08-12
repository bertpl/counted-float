"""Regenerate the shipped consensus flop-weight aggregates from the built-in source data.

Run via `make precompute-weights` whenever the source data under `data/sources/` changes. The
generated file is committed: it is read at runtime in place of re-deriving the aggregates, which
means parsing and aggregating every source file.

Aggregates are stored UNROUNDED, so one stored entry serves every rounding mode -- rounding is
applied by the caller, on top of the finished aggregate.

A test re-derives these aggregates and compares them against the committed file, so forgetting to
run this after a data change fails the suite rather than shipping stale weights.
"""

import json
import pathlib
import sys

from counted_float._core.counting.builtin_data._dataset import (
    DATA_PACKAGE,
    PRECOMPUTED_DIR,
    PRECOMPUTED_WEIGHTS_FILE,
    _aggregate_flop_weights_from_sources,
)

# The filters worth precomputing: the overall consensus (what the package configures by default)
# and the two coarse architecture splits. Anything else derives on demand.
PRECOMPUTED_KEY_FILTERS = ["", "arm", "x86"]


def main() -> int:
    """Derive each precomputed aggregate from the source tree and write them out."""
    # derived straight from the sources, never through the cached accessor -- that one reads this
    # file, and would happily regenerate it from itself
    aggregates = {
        key_filter: _aggregate_flop_weights_from_sources(key_filter) for key_filter in PRECOMPUTED_KEY_FILTERS
    }

    payload = {
        key_filter: json.loads(weights.model_dump_json())["weights"] for key_filter, weights in aggregates.items()
    }

    out_path = _repo_data_dir() / PRECOMPUTED_DIR / PRECOMPUTED_WEIGHTS_FILE
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=4) + "\n", encoding="utf-8")

    print(f"wrote {len(payload)} aggregates to {out_path}")
    return 0


def _repo_data_dir() -> pathlib.Path:
    """Return the in-repo data folder, so this writes to the source tree rather than an install."""
    return pathlib.Path(__file__).resolve().parent.parent / "src" / DATA_PACKAGE.replace(".", "/")


if __name__ == "__main__":
    sys.exit(main())
