import warnings

import pytest

from counted_float._core.evaluation import evaluate_counting_overhead


def test_evaluate_counting_overhead():
    # Rudimentary test to check the benchmark runs without errors
    result = evaluate_counting_overhead(t_target_sec=0.001)
    result.show()


def test_run_counted_float_benchmark_verbose_false_is_silent(capsys):
    # --- act --------------------------
    evaluate_counting_overhead(t_target_sec=0.001, verbose=False)

    # --- assert -----------------------
    assert capsys.readouterr().out == ""


# =================================================================================================
#  the deprecated home
# =================================================================================================
def test_the_old_benchmarking_name_still_resolves_to_the_moved_function(monkeypatch):
    # what keeps this a minor version: an existing import line must not stop working
    # --- arrange -----------------------------------------
    import counted_float.benchmarking as public_benchmarking

    # the alias binds itself on first use so it warns once per process; drop that binding so this
    # test sees the warning regardless of whether something earlier in the session already tripped it
    monkeypatch.delattr(public_benchmarking, "run_counted_float_benchmark", raising=False)

    # --- act ---------------------------------------------
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        alias = public_benchmarking.run_counted_float_benchmark

    # --- assert ------------------------------------------
    assert alias is evaluate_counting_overhead
    assert [w.category for w in caught] == [DeprecationWarning]
    assert "counted_float.evaluation" in str(caught[0].message)


def test_an_unknown_name_on_the_public_benchmarking_module_still_raises():
    # the alias hook must not swallow every miss
    # --- act / assert ------------------------------------
    import counted_float.benchmarking as public_benchmarking

    with pytest.raises(AttributeError, match="NoSuchThing"):
        _ = public_benchmarking.NoSuchThing
