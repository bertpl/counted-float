import subprocess
import sys
import textwrap

import pytest

from counted_float._core.counting.config import get_active_flop_weights, set_active_flop_weights
from counted_float._core.counting.config._config import Config
from counted_float._core.models import FlopType, FlopWeights


@pytest.mark.parametrize(
    ("getter", "setter"),
    [
        (get_active_flop_weights, set_active_flop_weights),
        (Config.get_flop_weights, Config.set_flop_weights),
        (get_active_flop_weights, Config.set_flop_weights),
        (Config.get_flop_weights, set_active_flop_weights),
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


@pytest.mark.parametrize("getter", [get_active_flop_weights, Config.get_flop_weights])
def test_flop_weight_getters_return_defensive_copies(getter):
    # --- act ---------------------------------------------
    flop_weights = getter()
    flop_weights.weights[FlopType.ADD] = -12345.0  # mutate the returned object

    # --- assert ------------------------------------------
    assert getter().weights[FlopType.ADD] != -12345.0


def test_bare_import_does_not_parse_builtin_data():
    # default consensus weights derive from every built-in data file, which is far too
    # expensive to pay at import time; that work must happen lazily on first weights access
    code = textwrap.dedent(
        """
        import sys
        opened = []
        def hook(event, args):
            if event == "open" and "counted_float/data" in str(args[0]).replace(chr(92), "/"):
                opened.append(str(args[0]))
        sys.addaudithook(hook)
        import counted_float
        sys.exit(1 if opened else 0)
        """
    )
    result = subprocess.run([sys.executable, "-c", code], check=False)  # noqa: S603 -- fixed args, no user input
    assert result.returncode == 0, "importing counted_float opened built-in data files"


def test_set_active_flop_weights_stores_a_copy():
    # --- arrange -----------------------------------------
    weights = FlopWeights(weights=dict.fromkeys(FlopType, 1.0))

    # --- act ---------------------------------------------
    set_active_flop_weights(weights)
    weights.weights[FlopType.ADD] = 999.0  # mutate the caller's instance after configuring

    # --- assert ------------------------------------------
    assert get_active_flop_weights().weights[FlopType.ADD] == 1.0
