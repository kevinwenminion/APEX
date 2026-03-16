"""LAMMPS binding for Surface."""

from apex.core.property._generic_lammps import make_generic_lammps_backend_summary
from apex.core.property._generic_lammps import make_generic_lammps_property_binding
from ..logic import Surface as SharedSurface


Surface = make_generic_lammps_property_binding(
    SharedSurface, "Surface", __name__
)

LAMMPS_BACKEND_SUMMARY = make_generic_lammps_backend_summary(
    property_type="surface",
    what_it_computes="surface energies for generated slab structures",
    default_cal_type="relaxation",
    default_cal_setting={
        "relax_pos": True,
        "relax_shape": True,
        "relax_vol": False,
    },
    structure_generation="generates slabs over Miller indices and perturbs xz before LAMMPS runs",
    task_metadata_files=["miller.json"],
)


__all__ = ["Surface", "LAMMPS_BACKEND_SUMMARY"]
