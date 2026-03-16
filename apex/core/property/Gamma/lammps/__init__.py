"""LAMMPS binding for Gamma."""

from apex.core.property._interaction_helpers import ensure_lammps_interaction
from ..logic import Gamma as SharedGamma
from .input import render_gamma_lammps_input


class Gamma(SharedGamma):
    """Gamma implementation bound to the LAMMPS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_lammps_interaction(inter_param))

    def _fix_task_output(self, task_dir, first_task):
        return None


__all__ = ["Gamma", "render_gamma_lammps_input"]
