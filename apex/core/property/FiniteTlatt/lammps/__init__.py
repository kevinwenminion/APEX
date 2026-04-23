"""LAMMPS binding for FiniteTlatt."""

from apex.core.property._interaction_helpers import ensure_lammps_interaction
from ..logic import FiniteTlatt as SharedFiniteTlatt
from .input import render_finitetlatt_lammps_input
from .variables import render_finitetlatt_variable_file


class FiniteTlatt(SharedFiniteTlatt):
    """FiniteTlatt implementation bound to the LAMMPS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_lammps_interaction(inter_param))


def get_lammps_file_manifest(model_files, default_manifest):
    """Return FiniteTlatt-specific LAMMPS transfer file lists."""
    manifest = {key: list(value) for key, value in default_manifest.items()}
    manifest["forward_files"] = ["in.lammps", "in.variable"] + list(model_files)
    manifest["forward_common_files"] = ["in.lammps", "in.variable"] + list(model_files)
    manifest["backward_files"] = [
        "log.lammps",
        "outlog",
        "dump.relax",
        "average_box.txt",
    ]
    return manifest


__all__ = [
    "FiniteTlatt",
    "get_lammps_file_manifest",
    "render_finitetlatt_lammps_input",
    "render_finitetlatt_variable_file",
]
