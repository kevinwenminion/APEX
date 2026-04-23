"""LAMMPS binding for Phonon."""

import os
import re
import shutil

from apex.core.property._interaction_helpers import ensure_lammps_interaction
from ..logic import Phonon as SharedPhonon
from .input import render_phonon_lammps_input


class Phonon(SharedPhonon):
    """Phonon implementation bound to the LAMMPS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_lammps_interaction(inter_param))
        if self.approach != "linear":
            raise TypeError('LAMMPS phonon currently only supports approach="linear"')

    def _make_backend_tasks(self, path_to_work, ptypes, ret, ret_force_read):
        task_list = []
        self._prepare_unitcell_poscar()

        task_path = os.path.join(path_to_work, "task.000000")
        os.makedirs(task_path, exist_ok=True)
        os.chdir(task_path)
        task_list.append(task_path)
        if os.path.isfile("POSCAR") or os.path.islink("POSCAR"):
            os.remove("POSCAR")
        os.symlink(os.path.join(path_to_work, "POSCAR-unitcell"), "POSCAR")

        with open("band.conf", "w") as fp:
            fp.write(ret_force_read)

        os.chdir(path_to_work)
        return task_list

    def _post_process_backend(self, task_list):
        for ii in task_list:
            os.chdir(ii)
            with open("in.lammps", "r") as f1:
                contents = f1.readlines()
            pair_line_id = None
            for jj, line in enumerate(contents):
                if re.search("pair_coeff", line):
                    pair_line_id = jj
                    break
            if pair_line_id is not None:
                del contents[pair_line_id + 1:]

            with open("in.lammps", "w") as f2:
                f2.write(self._ensure_deepmd_plugin_loaded("".join(contents)))

            with open("run_command", "w") as f3:
                f3.write(self._build_phonolammps_run_command())

    def _compute_backend_band(self, work_path, all_tasks):
        os.chdir(all_tasks[0])
        assert os.path.isfile("FORCE_CONSTANTS"), "FORCE_CONSTANTS not created"
        os.system(
            'phonopy --dim="%s %s %s" -c POSCAR band.conf'
            % (
                self.supercell_size[0],
                self.supercell_size[1],
                self.supercell_size[2],
            )
        )
        os.system("phonopy-bandplot --gnuplot band.yaml > band.dat")
        shutil.copyfile("band.dat", work_path / "band.dat")


def get_lammps_file_manifest(model_files, default_manifest):
    """Return Phonon-specific LAMMPS transfer file lists."""
    manifest = {key: list(value) for key, value in default_manifest.items()}
    manifest["backward_files"] = ["outlog", "FORCE_CONSTANTS"]
    return manifest


__all__ = ["Phonon", "get_lammps_file_manifest", "render_phonon_lammps_input"]
