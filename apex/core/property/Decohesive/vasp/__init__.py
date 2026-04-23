"""VASP binding for Decohesive."""

from apex.core.property._interaction_helpers import ensure_vasp_interaction
from ..logic import Decohesive as SharedDecohesive


class Decohesive(SharedDecohesive):
    """Decohesive implementation bound to the VASP backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_vasp_interaction(inter_param))


__all__ = ["Decohesive"]
