"""LAMMPS binding for Interstitial."""

from apex.core.property._generic_lammps import make_generic_lammps_backend_summary
from apex.core.property._generic_lammps import make_generic_lammps_property_binding
from ..logic import Interstitial as SharedInterstitial


Interstitial = make_generic_lammps_property_binding(
    SharedInterstitial, "Interstitial", __name__
)

LAMMPS_BACKEND_SUMMARY = make_generic_lammps_backend_summary(
    property_type="interstitial",
    what_it_computes="interstitial defect formation energies for generated defect structures",
    default_cal_type="relaxation",
    default_cal_setting={
        "relax_pos": True,
        "relax_shape": True,
        "relax_vol": True,
    },
    structure_generation="generates Voronoi or special interstitial structures before LAMMPS runs",
    task_metadata_files=["supercell.json", "interstitial_type.json"],
    property_metadata_files=["element.out"],
)


__all__ = ["Interstitial", "LAMMPS_BACKEND_SUMMARY"]
