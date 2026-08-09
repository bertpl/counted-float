"""Golden counting corpus: every counting decision of the cost model as one executable probe.

The corpus rows live in the `_corpus_*` modules (aggregated by `_corpus`), the execution and
assertion machinery in `_runner`, and the parametrized golden test in `test_golden_counting`.
Row IDs are frozen: a behavioral change lands as a deliberate edit to the row it changes,
never as a regenerated snapshot.
"""
