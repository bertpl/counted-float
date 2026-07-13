from counted_float._core.models import FlopWeights

from ._defaults import get_default_consensus_flop_weights


# =================================================================================================
#  Central class for weight configuration
# =================================================================================================
class Config:
    """Class to hold configuration settings for the counted_float package."""

    # -------------------------------------------------------------------------
    #  Internal State
    # -------------------------------------------------------------------------

    # these are the weights that are used to calculate weighted flop counts; update with
    # set_flop_weights(...).  None means "not initialized yet": the default consensus weights
    # are computed lazily on first access, since deriving them parses every built-in data file
    # (~0.8 s) — far too expensive to pay at import time for a feature many importers never use.
    __weights: FlopWeights | None = None

    # -------------------------------------------------------------------------
    #  Configuration Methods
    # -------------------------------------------------------------------------
    @classmethod
    def set_flop_weights(cls, weights: FlopWeights) -> None:
        """Set the weights for the flops used in the package.

        These weights will be used in any calculation of weighted flops, going forward.
        :param weights: FlopWeights instance containing the weights.
        """
        cls.__weights = weights

    @classmethod
    def get_flop_weights(cls) -> FlopWeights:
        """Get the currently configured flop weights.

        Returns a fresh deep copy; mutating it does not affect the configured weights.
        """
        if cls.__weights is None:
            cls.__weights = get_default_consensus_flop_weights()
        return cls.__weights.model_copy(deep=True)


# =================================================================================================
#  Functional accessors
# =================================================================================================
def set_active_flop_weights(weights: FlopWeights) -> None:
    """Set the weights for the flops used in the package.

    These weights will be used in any calculation of weighted flops, going forward.
    :param weights: FlopWeights instance containing the weights.
    """
    Config.set_flop_weights(weights)


def get_active_flop_weights() -> FlopWeights:
    """Get the currently configured flop weights."""
    return Config.get_flop_weights()
