"""Skip markers keyed on the same capability check the runtime guards use.

A test that needs an optional feature asks the question exactly the way production asks it, so a
test can never skip in an environment where the feature works, or run in one where it does not.
"""

import pytest

from counted_float._core.compatibility import is_available, missing_message


def needs(capability: str) -> pytest.MarkDecorator:
    """Skip unless the extra behind this capability is installed."""
    return pytest.mark.skipif(not is_available(capability), reason=missing_message(capability))
