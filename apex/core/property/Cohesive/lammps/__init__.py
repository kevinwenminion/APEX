"""LAMMPS binding for Cohesive."""

from apex.core.property._generic_lammps import make_generic_lammps_backend_summary
from apex.core.property._generic_lammps import make_generic_lammps_property_binding
from ..logic import Cohesive as SharedCohesive


Cohesive = make_generic_lammps_property_binding(
    SharedCohesive, "Cohesive", __name__
)

LAMMPS_BACKEND_SUMMARY = make_generic_lammps_backend_summary(
    property_type="cohesive",
    what_it_computes="cohesive energy curve from scaled bulk structures",
    default_cal_type="static",
    default_cal_setting={},
    structure_generation="scales the relaxed bulk structure over a lattice scan",
    task_metadata_files=["cohesive.json"],
)


__all__ = ["Cohesive", "LAMMPS_BACKEND_SUMMARY"]
