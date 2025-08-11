import pytest

from counted_float._core.counting.config import get_flop_weights, set_flop_weights
from counted_float._core.counting.config._config import Config
from counted_float._core.counting.models import FlopType, FlopWeights


@pytest.mark.parametrize(
    "getter, setter",
    [
        (get_flop_weights, set_flop_weights),
        (Config.get_flop_weights, Config.set_flop_weights),
        (get_flop_weights, Config.set_flop_weights),
        (Config.get_flop_weights, set_flop_weights),
    ],
)
def test_flop_weight_config(getter, setter):
    # --- arrange -----------------------------------------
    dummy_flop_weights_1 = FlopWeights(weights={flop_type: i for i, flop_type in enumerate(FlopType, start=1)})
    dummy_flop_weights_2 = FlopWeights(weights={flop_type: i for i, flop_type in enumerate(FlopType, start=2)})

    # --- act ---------------------------------------------
    flop_weights_a = getter()
    setter(dummy_flop_weights_1)
    flop_weights_b = getter()
    setter(dummy_flop_weights_2)
    flop_weights_c = getter()

    # --- assert ------------------------------------------
    assert flop_weights_a != flop_weights_b
    assert flop_weights_b != flop_weights_c
    assert flop_weights_b == dummy_flop_weights_1
    assert flop_weights_c == dummy_flop_weights_2
