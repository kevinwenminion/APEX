"""LAMMPS binding for Elastic."""

from apex.core.property._interaction_helpers import ensure_lammps_interaction
from ..logic import Elastic as SharedElastic


class Elastic(SharedElastic):
    """Elastic implementation bound to the LAMMPS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_lammps_interaction(inter_param))

    def _post_process_inputs(self, task_list):
        return None


__all__ = ["Elastic"]
