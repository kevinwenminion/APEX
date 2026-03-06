"""LAMMPS backend implementation entry for FiniteTlatt."""

from apex.core.property.lammps._helpers import ensure_interaction
from .logic import FiniteTlatt as BackendFiniteTlatt


class FiniteTlatt(BackendFiniteTlatt):
    """FiniteTlatt implementation bound to the LAMMPS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_interaction(inter_param))
