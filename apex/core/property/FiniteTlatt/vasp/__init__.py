"""VASP binding for FiniteTlatt."""

from apex.core.property._interaction_helpers import ensure_vasp_interaction
from ..logic import FiniteTlatt as SharedFiniteTlatt


class FiniteTlatt(SharedFiniteTlatt):
    """FiniteTlatt implementation bound to the VASP backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_vasp_interaction(inter_param))

    def _ensure_supported_backend(self):
        raise TypeError("FiniteTlatt only supports LAMMPS calculation")


__all__ = ["FiniteTlatt"]
