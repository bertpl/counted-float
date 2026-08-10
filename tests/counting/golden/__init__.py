"""The golden suite pins every counting decision of the cost model as one executable probe.

How the pieces fit:

- **The corpus** (`corpus/`) is a table of rows, one per counting decision. A row's snippet
  string — e.g. `"math.sqrt(num(2.0))"` — is simultaneously the probe (compiled at import
  into `lambda num: ...`), the test ID, and the expression a failure message shows. `num` is
  the injected number type: `CountedFloat` for the counted run, plain `float` for the twin
  run. Each row states its expected flop counts, exact result type (or exception), the
  cost-model citations that force the outcome, and optional gates.
- **The helpers** (`helpers/`) execute a probe under one of three context regimes — counting
  (a fresh `FlopCountingContext`), paused, or outside any context — and reduces outcomes to
  bit-comparable form.
- **The golden test** (`test_golden_counting`) drives every row across regime × repetition
  count: exact full-dict counts scaling linearly with repetitions, exact result types, and a
  plain-float twin that must count nothing and reproduce the outcome bit-for-bit.
- **The meta-tests** (`test_corpus_coverage`) hold the corpus to a closed world: every
  patched `math` name and `CountedFloat` dunder must be reached by some row (recorded by
  execution, never declared), and every citation must resolve to a live docs anchor.

Row IDs are frozen: a behavioral change lands as a deliberate edit to the row it changes,
never as a regenerated snapshot.
"""
