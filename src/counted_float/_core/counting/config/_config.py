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
    # are computed lazily on first access, since deriving them parses and aggregates every
    # built-in data file — far too expensive to pay at import time for a feature many
    # importers never use.
    __weights: FlopWeights | None = None

    # -------------------------------------------------------------------------
    #  Configuration Methods
    # -------------------------------------------------------------------------
    @classmethod
    def set_flop_weights(cls, weights: FlopWeights) -> None:
        """Set the weights for the flops used in the package.

        These weights will be used in any calculation of weighted flops, going forward.

        Stores a deep copy, so later mutating the passed instance does not reconfigure the
        package -- the mirror image of the value semantics get_flop_weights() provides.

        :param weights: FlopWeights instance containing the weights.
        """
        cls.__weights = weights.model_copy(deep=True)

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
    """Get the currently configured flop weights.

    Returns a fresh deep copy, deliberately: the returned object is yours to inspect or modify
    without reconfiguring the package. Mutating it therefore has no effect on what gets counted --
    to change the active weights, pass the modified instance to set_active_flop_weights().
    """
    return Config.get_flop_weights()
