# Deprecations

Everything below still works today, and is removed in **3.0.0** (no timeline
pinned). Nothing else is scheduled for removal.

## The `numba` extra → `benchmarking`

```
pip install counted-float[benchmarking]   # replaces counted-float[numba]
```

Same dependency set. The one entry that cannot warn: an extra is packaging
metadata, no code runs — an unchanged install string simply stops resolving in
3.0.0, so update pins now.

## The `benchmark-counted-float` command → `evaluate-overhead`

```bash
counted_float evaluate-overhead   # replaces benchmark-counted-float
```

The old name still runs, delegates, and prints a notice to stderr; it is hidden
from `--help`.

## `run_counted_float_benchmark` → `evaluate_counting_overhead`

```python
from counted_float.evaluation import evaluate_counting_overhead
# replaces: from counted_float.benchmarking import run_counted_float_benchmark
```

The old import still resolves and raises a `DeprecationWarning` (silent by
default — `python -W default::DeprecationWarning ...` shows it).
