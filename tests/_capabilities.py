"""Skip markers keyed on what the running environment can actually import.

Tests come in three shapes here, and each gets a marker rather than an inline condition, so that a
reader sees *why* a test is conditional without decoding a boolean:

- needs an optional capability          -> ``@needs(CAP_X)``
- needs numba specifically              -> ``@needs_numba`` / ``@needs_no_numba``

numba gets its own pair because it is not a capability: it is shimmed, so its absence changes how
fast and how accurate the benchmarks are, not whether they run. Both directions exist because the
shim's own code paths are only reachable when the real thing is absent.
"""

import pytest

from counted_float._core.compatibility import Capability, is_importable


def needs(capability: Capability) -> pytest.MarkDecorator:
    """Skip unless the extra behind this capability is installed."""
    return pytest.mark.skipif(
        not capability.is_available(),
        reason=f'needs the "{capability.extra}" extra',
    )


needs_numba = pytest.mark.skipif(
    not is_importable("numba"),
    reason="needs real numba timings, not the identity-decorator shim",
)

needs_no_numba = pytest.mark.skipif(
    is_importable("numba"),
    reason="exercises the shim, which only stands in when numba is absent",
)
