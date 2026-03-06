"""ABACUS backend implementation entry for Gamma."""

from apex.core.property.abacus._helpers import ensure_interaction
from .logic import Gamma as BackendGamma


class Gamma(BackendGamma):
    """Gamma implementation bound to the ABACUS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_interaction(inter_param))
