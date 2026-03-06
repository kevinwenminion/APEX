"""Helpers for LAMMPS backend property wrappers."""

from apex.core.calculator import LAMMPS_INTER_TYPE


LAMMPS_BACKEND_TYPES = set(LAMMPS_INTER_TYPE) | {"lammps"}


def ensure_interaction(inter_param):
    """Normalize and validate interaction for LAMMPS backend properties."""
    inter = dict(inter_param or {})
    if not inter:
        inter["type"] = "lammps"
    if inter.get("type") not in LAMMPS_BACKEND_TYPES:
        raise RuntimeError("LAMMPS property implementation requires a LAMMPS interaction.type")
    return inter
