"""ABACUS binding for Interstitial."""

import os

from apex.core.calculator.lib import abacus_utils
from apex.core.property._interaction_helpers import ensure_abacus_interaction
from ..logic import Interstitial as SharedInterstitial


class Interstitial(SharedInterstitial):
    """Interstitial implementation bound to the ABACUS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_abacus_interaction(inter_param))

    def _resolve_equilibrium_structure(self, path_to_equi):
        contcar = os.path.join(path_to_equi, abacus_utils.final_stru(path_to_equi))
        return contcar, os.path.join(path_to_equi, "STRU"), "STRU"

    def _load_equilibrium_structure(self, equi_contcar):
        return abacus_utils.stru2Structure(equi_contcar)

    def _finalize_generated_tasks(self, total_task):
        for ii in range(total_task):
            output_task = os.path.join(self.path_to_work, f"task.{ii:06d}")
            os.chdir(output_task)
            abacus_utils.poscar2stru("POSCAR", self.inter_param, "STRU")


__all__ = ["Interstitial"]
