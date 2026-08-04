# Deprecations

What is scheduled to be removed, and what to use instead.

Everything listed here still works today. Each entry keeps working for the rest
of the `2.x` series and is removed at **the next major release** — that is the
whole of the commitment: no date is promised, and no other removal is planned.
When this page is empty, nothing is pending.

This is the live inventory. The [changelog](changelog.md) records *when* each
name was deprecated; this page records what is *still* deprecated, and shrinks
as entries are removed.

## Pending removal at the next major

All three were deprecated in **2.1.0**, and are renames rather than withdrawals
— the functionality stays, under a name that says what it does. Each measures
this library's own overhead, which the old names described as benchmarking a
machine.

### The `numba` extra → `benchmarking`

```
pip install counted-float[numba]         # deprecated
pip install counted-float[benchmarking]  # use this
```

The old extra resolves to exactly the same dependency set, so nothing about an
existing install changes until it is removed.

**This is the one entry you cannot be warned about at runtime.** An extra is
packaging metadata, not code, so nothing runs and nothing can print a notice —
an install string left unchanged simply stops resolving at the next major.
Anything pinning `counted-float[numba]` is worth updating now.

### The `benchmark-counted-float` command → `evaluate-overhead`

```bash
counted_float benchmark-counted-float   # deprecated
counted_float evaluate-overhead         # use this
```

The old name still runs and delegates to the new one, printing a notice to
stderr. It is hidden from `--help`, since it exists for command lines already
written rather than for new ones. See the
[CLI reference](cli.md) for what the command does.

### `run_counted_float_benchmark` → `evaluate_counting_overhead`

```python
from counted_float.benchmarking import run_counted_float_benchmark  # deprecated
from counted_float.evaluation import evaluate_counting_overhead     # use this
```

The old name still resolves from `counted_float.benchmarking` and raises a
`DeprecationWarning` once per process. The function itself is unchanged — it
moved to `counted_float.evaluation`, alongside the rest of the library's
self-measurement.

Note that `DeprecationWarning` is silent by default in Python. To see it, run
with warnings enabled:

```bash
python -W default::DeprecationWarning your_script.py
```

## What is not on this list

**Nothing else is scheduled for removal.** The public API is deliberately small
and is not expected to shed anything beyond the three names above. Behavior that
falls outside the counting model is not a deprecation — it is documented, and
stays documented, under [known limitations](known_limitations.md).
