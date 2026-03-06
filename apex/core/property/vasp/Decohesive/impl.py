"""VASP backend implementation entry for Decohesive."""

from apex.core.property.vasp._helpers import ensure_interaction
from .logic import Decohesive as BackendDecohesive


class Decohesive(BackendDecohesive):
    """Decohesive implementation bound to the VASP backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_interaction(inter_param))
