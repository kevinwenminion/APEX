"""ABACUS binding for EOS."""

import os

import numpy as np

from apex.core.calculator.lib import abacus_scf
from apex.core.calculator.lib import abacus_utils
from apex.core.property._interaction_helpers import ensure_abacus_interaction
from ..logic import EOS as SharedEOS


class EOS(SharedEOS):
    """EOS implementation bound to the ABACUS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_abacus_interaction(inter_param))

    def _resolve_equilibrium_structure(self, path_to_equi):
        return os.path.join(path_to_equi, abacus_utils.final_stru(path_to_equi))

    def _read_volume_per_atom(self, equi_structure):
        stru_data = abacus_scf.get_abacus_STRU(equi_structure)
        return abs(np.linalg.det(stru_data["cells"])) / np.array(
            stru_data["atom_numbs"]
        ).sum()

    def _task_structure_names(self):
        return "STRU", "STRU.orig"

    def _scale_structure(self, src, dst, scale):
        abacus_utils.stru_scale(src, dst, scale)


__all__ = ["EOS"]
