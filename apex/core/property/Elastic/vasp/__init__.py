"""VASP binding for Elastic."""

from apex.core.property._interaction_helpers import ensure_vasp_interaction
from ..logic import Elastic as SharedElastic


class Elastic(SharedElastic):
    """Elastic implementation bound to the VASP backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_vasp_interaction(inter_param))


__all__ = ["Elastic"]
