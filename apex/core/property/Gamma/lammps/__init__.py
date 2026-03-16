"""LAMMPS binding for Gamma."""

import os

from apex.core.property._interaction_helpers import ensure_lammps_interaction
from ..logic import Gamma as SharedGamma


class Gamma(SharedGamma):
    """Gamma implementation bound to the LAMMPS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_lammps_interaction(inter_param))

    def _fix_task_output(self, task_dir, first_task):
        if first_task:
            self._Gamma__inLammpes_fix(os.path.join(task_dir, "in.lammps"))


__all__ = ["Gamma"]
