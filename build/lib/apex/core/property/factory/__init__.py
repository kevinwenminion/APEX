"""Software-first property factory.

Dispatch order is intentionally:
1) choose backend software (vasp/abacus/lammps-like),
2) choose property implementation under that backend registry.
"""

from typing import Dict, Mapping, Type

from apex.core.calculator import LAMMPS_INTER_TYPE
from apex.core.property.abacus import PROPERTY_CLASS_MAP as ABACUS_PROPERTY_CLASS_MAP
from apex.core.property.lammps import PROPERTY_CLASS_MAP as LAMMPS_PROPERTY_CLASS_MAP
from apex.core.property.vasp import PROPERTY_CLASS_MAP as VASP_PROPERTY_CLASS_MAP


def _select_registry(inter_type: str) -> Mapping[str, Type]:
    if inter_type == "vasp":
        return VASP_PROPERTY_CLASS_MAP
    if inter_type == "abacus":
        return ABACUS_PROPERTY_CLASS_MAP
    if inter_type == "lammps" or inter_type in LAMMPS_INTER_TYPE:
        return LAMMPS_PROPERTY_CLASS_MAP
    raise RuntimeError(f"unsupported interaction {inter_type}")


def make_property_instance(parameters: Dict, inter_param: Dict):
    """Create property instance by backend first, then property type."""
    prop_type = parameters["type"]
    inter_type = (inter_param or {}).get("type", "vasp")
    registry = _select_registry(inter_type)

    prop_cls = registry.get(prop_type)
    if prop_cls is None:
        raise RuntimeError(
            f"unknown APEX type {prop_type} for interaction {inter_type}"
        )
    return prop_cls(parameters, inter_param)
