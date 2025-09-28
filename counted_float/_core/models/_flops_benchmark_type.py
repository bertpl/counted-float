from counted_float._core.compatibility import StrEnum


class FlopsBenchmarkType(StrEnum):
    # TODO: extend when we actually implement these benchmarks
    BASELINE = "baseline"
    ADD = "add"
    SUB = "sub"
