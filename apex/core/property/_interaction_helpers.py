"""Backend interaction validators for property-first bindings."""

from apex.core.calculator import LAMMPS_INTER_TYPE


LAMMPS_BACKEND_TYPES = set(LAMMPS_INTER_TYPE) | {"lammps"}


def ensure_vasp_interaction(inter_param):
    """Normalize and validate interaction for VASP-bound properties."""
    inter = dict(inter_param or {})
    if not inter:
        inter["type"] = "vasp"
    if inter.get("type") != "vasp":
        raise RuntimeError("VASP property implementation requires interaction.type=vasp")
    return inter


def ensure_abacus_interaction(inter_param):
    """Normalize and validate interaction for ABACUS-bound properties."""
    inter = dict(inter_param or {})
    if not inter:
        inter["type"] = "abacus"
    if inter.get("type") != "abacus":
        raise RuntimeError(
            "ABACUS property implementation requires interaction.type=abacus"
        )
    return inter


def ensure_lammps_interaction(inter_param):
    """Normalize and validate interaction for LAMMPS-bound properties."""
    inter = dict(inter_param or {})
    if not inter:
        inter["type"] = "lammps"
    if inter.get("type") not in LAMMPS_BACKEND_TYPES:
        raise RuntimeError(
            "LAMMPS property implementation requires a LAMMPS interaction.type"
        )
    return inter
