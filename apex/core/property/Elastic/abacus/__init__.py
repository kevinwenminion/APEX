"""ABACUS binding for Elastic."""

import os

from apex.core.calculator.lib import abacus_scf
from apex.core.calculator.lib import abacus_utils
from apex.core.property._interaction_helpers import ensure_abacus_interaction
from ..logic import Elastic as SharedElastic


class Elastic(SharedElastic):
    """Elastic implementation bound to the ABACUS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_abacus_interaction(inter_param))

    def _resolve_equilibrium_structure(self, path_to_equi):
        return os.path.join(path_to_equi, abacus_utils.final_stru(path_to_equi)), "STRU"

    def _load_equilibrium_structure(self, equi_contcar):
        return abacus_utils.stru2Structure(equi_contcar)

    def _finalize_task_structure(self):
        abacus_utils.poscar2stru("POSCAR", self.inter_param, "STRU")

    def _post_process_inputs(self, task_list):
        POSCAR = "STRU"
        INCAR = "INPUT"
        KPOINTS = "KPT"
        cwd = os.getcwd()
        poscar_start = os.path.abspath(os.path.join(task_list[0], "..", POSCAR))
        os.chdir(os.path.join(task_list[0], ".."))
        if os.path.isfile(os.path.join(task_list[0], INCAR)):
            input_aba = abacus_scf.get_abacus_input_parameters("INPUT")
            if "kspacing" in input_aba:
                kspacing = float(input_aba["kspacing"])
                kpt = abacus_utils.make_kspacing_kpt(poscar_start, kspacing)
                kpt += [0, 0, 0]
                abacus_utils.write_kpt("KPT", kpt)
                del input_aba["kspacing"]
                os.remove("INPUT")
                abacus_utils.write_input("INPUT", input_aba)
            else:
                os.rename(os.path.join(task_list[0], "KPT"), "./KPT")

            kpoints_universal = os.path.abspath(os.path.join(task_list[0], "..", KPOINTS))
            for ii in task_list:
                if os.path.exists(os.path.join(ii, KPOINTS)):
                    os.remove(os.path.join(ii, KPOINTS))
                os.chdir(ii)
                os.symlink(os.path.relpath(kpoints_universal), KPOINTS)
        os.chdir(cwd)


__all__ = ["Elastic"]
