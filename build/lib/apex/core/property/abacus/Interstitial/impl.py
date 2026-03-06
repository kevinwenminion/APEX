"""ABACUS backend implementation entry for Interstitial."""

from apex.core.property.abacus._helpers import ensure_interaction
from .logic import Interstitial as BackendInterstitial


class Interstitial(BackendInterstitial):
    """Interstitial implementation bound to the ABACUS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_interaction(inter_param))
