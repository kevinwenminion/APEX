"""ABACUS binding for Surface."""

import os

import dpdata
from pymatgen.core.structure import Structure

from apex.core.calculator.lib import abacus_utils
from apex.core.calculator.lib import vasp_utils
from apex.core.property._interaction_helpers import ensure_abacus_interaction
from ..logic import Surface as SharedSurface


class Surface(SharedSurface):
    """Surface implementation bound to the ABACUS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_abacus_interaction(inter_param))

    def _resolve_equilibrium_structure(self, path_to_equi):
        return os.path.join(path_to_equi, abacus_utils.final_stru(path_to_equi))

    def _read_equilibrium_structure(self, equi_contcar):
        stru = dpdata.System(equi_contcar, fmt="stru")
        stru.to("contcar", "CONTCAR.tmp")
        try:
            ptypes = vasp_utils.get_poscar_types("CONTCAR.tmp")
            ss = Structure.from_file("CONTCAR.tmp")
        finally:
            os.remove("CONTCAR.tmp")
        return ptypes, ss

    def _task_structure_name(self):
        return "STRU"

    def _finalize_task_structure(self):
        abacus_utils.poscar2stru("POSCAR", self.inter_param, "STRU")


__all__ = ["Surface"]
