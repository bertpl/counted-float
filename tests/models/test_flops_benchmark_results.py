import json

import pytest
from pydantic import ValidationError

from counted_float import BuiltInData
from counted_float._core.models import FlopsBenchmarkResults, FlopType


def test_flops_benchmark_results_show():
    """Minimal test to check if JsonReprModel.show() at least does not raise exceptions."""

    # --- arrange -----------------------------------------
    flops_benchmark_results: FlopsBenchmarkResults = list(BuiltInData.benchmarks().values()).pop()

    # --- act ---------------------------------------------
    str(flops_benchmark_results)
    repr(flops_benchmark_results)
    flops_benchmark_results.show()


def test_estimated_flop_latencies_serialize_on_stable_names():
    # --- arrange -----------------------------------------
    result = list(BuiltInData.benchmarks().values()).pop()

    # --- act ---------------------------------------------
    on_disk = json.loads(result.model_dump_json())["estimated_flop_latencies"]

    # --- assert ------------------------------------------
    assert "ADD" in on_disk  # stable name on disk...
    assert "x+y" not in on_disk  # ...not the label


def test_legacy_label_keyed_latencies_raise():
    # --- arrange -----------------------------------------
    result = list(BuiltInData.benchmarks().values()).pop()
    # rewrite this result's latency keys to the legacy display-label form a pre-2.0.0 file used;
    # those files must be regenerated, and the failure is loud rather than silent missing data
    as_dict = json.loads(result.model_dump_json())
    as_dict["estimated_flop_latencies"] = {
        FlopType[key].label: value for key, value in as_dict["estimated_flop_latencies"].items()
    }

    # --- act / assert ------------------------------------
    with pytest.raises(ValidationError, match="unrecognized flop-type key"):
        FlopsBenchmarkResults.model_validate_json(json.dumps(as_dict))
