"""ABACUS backend implementation entry for Elastic."""

from apex.core.property.abacus._helpers import ensure_interaction
from .logic import Elastic as BackendElastic


class Elastic(BackendElastic):
    """Elastic implementation bound to the ABACUS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_interaction(inter_param))
