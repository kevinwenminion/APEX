"""LAMMPS binding for Vacancy."""

from apex.core.property._generic_lammps import make_generic_lammps_backend_summary
from apex.core.property._generic_lammps import make_generic_lammps_property_binding
from ..logic import Vacancy as SharedVacancy


Vacancy = make_generic_lammps_property_binding(
    SharedVacancy, "Vacancy", __name__
)

LAMMPS_BACKEND_SUMMARY = make_generic_lammps_backend_summary(
    property_type="vacancy",
    what_it_computes="vacancy defect formation energies for generated defect structures",
    default_cal_type="relaxation",
    default_cal_setting={
        "relax_pos": True,
        "relax_shape": True,
        "relax_vol": True,
    },
    structure_generation="removes one site from a generated supercell before LAMMPS runs",
    task_metadata_files=["supercell.json"],
)


__all__ = ["Vacancy", "LAMMPS_BACKEND_SUMMARY"]
