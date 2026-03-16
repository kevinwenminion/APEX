"""LAMMPS binding for Cohesive."""

from apex.core.property._interaction_helpers import ensure_lammps_interaction
from ..logic import Cohesive as SharedCohesive


class Cohesive(SharedCohesive):
    """Cohesive implementation bound to the LAMMPS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_lammps_interaction(inter_param))


__all__ = ["Cohesive"]
