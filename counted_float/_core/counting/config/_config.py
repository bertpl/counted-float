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

    # these are the weights that are used to calculate weighted flop counts; update with set_flop_weights(...)
    __weights: FlopWeights = get_default_consensus_flop_weights()

    # -------------------------------------------------------------------------
    #  Configuration Methods
    # -------------------------------------------------------------------------
    @classmethod
    def set_flop_weights(cls, weights: FlopWeights):
        """
        Set the weights for the flops used in the package.  These weights will be used in any calculation of
        weighted flops, going forward.
        :param weights: FlopWeights instance containing the weights.
        """
        cls.__weights = weights

    @classmethod
    def get_flop_weights(cls) -> FlopWeights:
        """
        Get the currently configured flop weights.
        """
        return cls.__weights.model_copy()


# =================================================================================================
#  Functional accessors
# =================================================================================================
def set_active_flop_weights(weights: FlopWeights):
    """
    Set the weights for the flops used in the package.  These weights will be used in any calculation of
    weighted flops, going forward.
    :param weights: FlopWeights instance containing the weights.
    """
    Config.set_flop_weights(weights)


def get_active_flop_weights() -> FlopWeights:
    """
    Get the currently configured flop weights.
    """
    return Config.get_flop_weights()
