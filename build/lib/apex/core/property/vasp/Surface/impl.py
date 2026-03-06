"""VASP backend implementation entry for Surface."""

from apex.core.property.vasp._helpers import ensure_interaction
from .logic import Surface as BackendSurface


class Surface(BackendSurface):
    """Surface implementation bound to the VASP backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_interaction(inter_param))
