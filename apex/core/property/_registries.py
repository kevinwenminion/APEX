"""Canonical property registries keyed by backend family."""

from copy import deepcopy
from importlib import import_module
from pathlib import Path


_PROPERTY_ROOT = Path(__file__).resolve().parent
_BACKENDS = ("vasp", "abacus", "lammps")
_SKIP_DIRS = {"__pycache__", "factory"}


def _iter_property_packages():
    for path in sorted(_PROPERTY_ROOT.iterdir()):
        if not path.is_dir():
            continue
        if path.name in _SKIP_DIRS or path.name.startswith("_"):
            continue
        if not (path / "__init__.py").is_file():
            continue
        yield path.name


def _load_backend_module(property_name: str, backend: str):
    return import_module(f"apex.core.property.{property_name}.{backend}")


def _load_backend_property_class(module, property_name: str, backend: str):
    property_cls = getattr(module, property_name, None)
    if property_cls is None:
        raise ImportError(
            f"Backend module apex.core.property.{property_name}.{backend} "
            f"must export class {property_name}"
        )
    return property_cls


def _load_lammps_backend_summary(module, property_name: str):
    summary = getattr(module, "LAMMPS_BACKEND_SUMMARY", None)
    if summary is None:
        return None
    summary = deepcopy(summary)
    summary.setdefault("property_type", property_name.lower())
    return summary


def _build_property_class_map(backend: str):
    registry = {}
    for property_name in _iter_property_packages():
        backend_init = _PROPERTY_ROOT / property_name / backend / "__init__.py"
        if not backend_init.is_file():
            continue
        module = _load_backend_module(property_name, backend)
        property_cls = _load_backend_property_class(module, property_name, backend)
        property_type = getattr(module, "PROPERTY_TYPE", property_name.lower())
        registry[property_type] = property_cls
    return registry


def _build_lammps_backend_summary_map():
    registry = {}
    for property_name in _iter_property_packages():
        backend_init = _PROPERTY_ROOT / property_name / "lammps" / "__init__.py"
        if not backend_init.is_file():
            continue
        module = _load_backend_module(property_name, "lammps")
        summary = _load_lammps_backend_summary(module, property_name)
        if summary is None:
            continue
        property_type = getattr(module, "PROPERTY_TYPE", property_name.lower())
        registry[property_type] = summary
    return registry


VASP_PROPERTY_CLASS_MAP = _build_property_class_map("vasp")
ABACUS_PROPERTY_CLASS_MAP = _build_property_class_map("abacus")
LAMMPS_PROPERTY_CLASS_MAP = _build_property_class_map("lammps")
LAMMPS_BACKEND_SUMMARY_MAP = _build_lammps_backend_summary_map()
