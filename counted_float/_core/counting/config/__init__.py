from ..models import FlopWeights


def set_flop_weights(weights: FlopWeights):
    """
    Set the weights for the flops used in the package.  These weights will be used in any calculation of
    weighted flops, going forward.
    :param weights: FlopWeights instance containing the weights.
    """
    from ._config import Config

    Config.set_flop_weights(weights)


def get_flop_weights() -> FlopWeights:
    """
    Get the currently configured flop weights.
    """
    from ._config import Config

    return Config.get_flop_weights()
