"""Helpers for generic LAMMPS-backed property bindings."""

from copy import deepcopy

from apex.core.property._interaction_helpers import ensure_lammps_interaction


def make_generic_lammps_property_binding(shared_cls, class_name, module_name):
    """Create a thin LAMMPS binding for properties with no backend-local hooks."""

    class GenericLammpsProperty(shared_cls):
        def __init__(self, parameter, inter_param=None):
            super().__init__(parameter, ensure_lammps_interaction(inter_param))

    GenericLammpsProperty.__name__ = class_name
    GenericLammpsProperty.__qualname__ = class_name
    GenericLammpsProperty.__module__ = module_name
    GenericLammpsProperty.__doc__ = (
        f"{class_name} implementation bound to the generic LAMMPS backend."
    )
    return GenericLammpsProperty


def make_generic_lammps_backend_summary(
    *,
    property_type,
    what_it_computes,
    default_cal_type,
    default_cal_setting,
    structure_generation,
    task_metadata_files=None,
    property_metadata_files=None,
    notes=None,
):
    """Create normalized metadata for generic LAMMPS-backed properties."""
    return {
        "property_type": property_type,
        "input_mode": "generic",
        "what_it_computes": what_it_computes,
        "default_cal_type": default_cal_type,
        "default_cal_setting": deepcopy(default_cal_setting),
        "structure_generation": structure_generation,
        "task_metadata_files": list(task_metadata_files or []),
        "property_metadata_files": list(property_metadata_files or []),
        "notes": list(notes or []),
    }
