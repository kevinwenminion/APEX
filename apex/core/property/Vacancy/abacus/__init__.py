"""ABACUS binding for Vacancy."""

import os

from apex.core.calculator.lib import abacus_utils
from apex.core.property._interaction_helpers import ensure_abacus_interaction
from ..logic import Vacancy as SharedVacancy


class Vacancy(SharedVacancy):
    """Vacancy implementation bound to the ABACUS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_abacus_interaction(inter_param))

    def _resolve_equilibrium_structure(self, path_to_equi):
        return os.path.join(path_to_equi, abacus_utils.final_stru(path_to_equi)), "STRU"

    def _load_equilibrium_structure(self, equi_contcar):
        return abacus_utils.stru2Structure(equi_contcar)

    def _finalize_task_structure(self):
        abacus_utils.poscar2stru("POSCAR", self.inter_param, "STRU")


__all__ = ["Vacancy"]
