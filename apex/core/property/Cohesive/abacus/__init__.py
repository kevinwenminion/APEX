"""ABACUS binding for Cohesive."""

import os

import numpy as np

from apex.core.calculator.lib import abacus_scf
from apex.core.calculator.lib import abacus_utils
from apex.core.property._interaction_helpers import ensure_abacus_interaction
from ..logic import Cohesive as SharedCohesive


class Cohesive(SharedCohesive):
    """Cohesive implementation bound to the ABACUS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_abacus_interaction(inter_param))

    def _resolve_equilibrium_structure(self, path_to_equi: str) -> str:
        return os.path.join(path_to_equi, abacus_utils.final_stru(path_to_equi))

    def _read_equilibrium_lattice(self, equi_structure: str) -> float:
        stru_data = abacus_scf.get_abacus_STRU(equi_structure)
        return np.linalg.norm(stru_data["cells"], axis=1)[0]

    def _task_structure_names(self):
        return "STRU", "STRU.orig"

    def _scale_structure(self, src: str, dst: str, scale_val: float) -> None:
        abacus_utils.stru_scale(src, dst, scale_val)


__all__ = ["Cohesive"]
