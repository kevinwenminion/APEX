"""LAMMPS binding for Decohesive."""

from apex.core.property._generic_lammps import make_generic_lammps_backend_summary
from apex.core.property._generic_lammps import make_generic_lammps_property_binding
from ..logic import Decohesive as SharedDecohesive


Decohesive = make_generic_lammps_property_binding(
    SharedDecohesive, "Decohesive", __name__
)

LAMMPS_BACKEND_SUMMARY = make_generic_lammps_backend_summary(
    property_type="decohesive",
    what_it_computes="decohesion energy curve from slabs with increasing vacuum separation",
    default_cal_type="static",
    default_cal_setting={
        "relax_pos": False,
        "relax_shape": False,
        "relax_vol": False,
    },
    structure_generation="builds one slab orientation and sweeps vacuum size",
    task_metadata_files=["decohesive.json"],
)


__all__ = ["Decohesive", "LAMMPS_BACKEND_SUMMARY"]
