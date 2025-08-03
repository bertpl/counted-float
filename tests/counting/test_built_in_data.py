from counted_float._core.counting._builtin_data import BuiltInData
from counted_float._core.counting.models import FlopsBenchmarkResults, InstructionLatencies


def test_builtin_data_benchmarks():
    # --- act ---------------------------------------------
    result = BuiltInData.benchmarks()

    # --- assert ------------------------------------------
    assert all(isinstance(v, FlopsBenchmarkResults) for v in result.values())


def test_builtin_data_specs():
    # --- act ---------------------------------------------
    result = BuiltInData.specs()

    # --- assert ------------------------------------------
    assert all(isinstance(v, InstructionLatencies) for v in result.values())
