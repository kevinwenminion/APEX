"""ABACUS binding for Phonon."""

import glob
import logging
import os
import subprocess

import dpdata
from pymatgen.core.structure import Structure

from apex.core.calculator.lib import abacus_utils
from apex.core.calculator.lib import vasp_utils
from apex.core.property._interaction_helpers import ensure_abacus_interaction
from ..logic import Phonon as SharedPhonon


class Phonon(SharedPhonon):
    """Phonon implementation bound to the ABACUS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_abacus_interaction(inter_param))

    def _resolve_equilibrium_structure(self, path_to_equi):
        return os.path.join(path_to_equi, abacus_utils.final_stru(path_to_equi)), "STRU"

    def _load_equilibrium_structure(self, equi_contcar):
        stru = dpdata.System(equi_contcar, fmt="stru")
        stru.to("contcar", "CONTCAR.tmp")
        try:
            ptypes = vasp_utils.get_poscar_types("CONTCAR.tmp")
            ss = Structure.from_file("CONTCAR.tmp")
        finally:
            os.remove("CONTCAR.tmp")
        return ptypes, ss

    def _make_backend_tasks(self, path_to_work, ptypes, ret, ret_force_read):
        task_list = []
        ret_sc = "DIM=%s %s %s\n" % (
            self.supercell_size[0],
            self.supercell_size[1],
            self.supercell_size[2],
        )
        ret_sc += "ATOM_NAME ="
        for atom in ptypes:
            ret_sc += " %s" % atom
        ret_sc += "\n"
        with open("setting.conf", "w") as fp:
            fp.write(ret_sc)

        orb_file = self.inter_param.get("orb_files", None)
        abacus_utils.append_orb_file_to_stru("STRU", orb_file, prefix="pp_orb")
        subprocess.call("phonopy setting.conf --abacus -d", shell=True)

        with open("band.conf", "w") as fp:
            fp.write(ret)

        stru_list = glob.glob("STRU-0*")
        for ii in range(len(stru_list)):
            task_path = os.path.join(path_to_work, "task.%06d" % ii)
            os.makedirs(task_path, exist_ok=True)
            os.chdir(task_path)
            task_list.append(task_path)
            os.symlink(os.path.join(path_to_work, stru_list[ii]), "STRU")
            os.symlink(os.path.join(path_to_work, "STRU"), "STRU.ori")
            os.symlink(os.path.join(path_to_work, "band.conf"), "band.conf")
            os.symlink(os.path.join(path_to_work, "phonopy_disp.yaml"), "phonopy_disp.yaml")
            try:
                os.symlink(os.path.join(path_to_work, "KPT"), "KPT")
            except OSError:
                pass

        os.chdir(path_to_work)
        return task_list

    def _compute_backend_band(self, work_path, all_tasks):
        self.check_same_copy("task.000000/band.conf", "band.conf")
        self.check_same_copy("task.000000/STRU.ori", "STRU")
        self.check_same_copy("task.000000/phonopy_disp.yaml", "phonopy_disp.yaml")
        os.system("phonopy -f task.0*/OUT.ABACUS/running_scf.log")
        if os.path.exists("FORCE_SETS"):
            print("FORCE_SETS is created")
        else:
            logging.warning("FORCE_SETS can not be created")
        os.system("phonopy band.conf --abacus")
        os.system("phonopy-bandplot --gnuplot band.yaml > band.dat")


__all__ = ["Phonon"]
