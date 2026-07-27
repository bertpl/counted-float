"""Skip markers keyed on the same capability check the runtime guards use.

A test that needs an optional feature asks the question exactly the way production asks it, so a
test can never skip in an environment where the feature works, or run in one where it does not.
"""

import pytest

from counted_float._core.compatibility import Capability


def needs(capability: Capability) -> pytest.MarkDecorator:
    """Skip unless the extra behind this capability is installed."""
    return pytest.mark.skipif(not capability.is_available(), reason=capability.missing_message())
