"""LAMMPS binding for EOS."""

from apex.core.property._interaction_helpers import ensure_lammps_interaction
from ..logic import EOS as SharedEOS


class EOS(SharedEOS):
    """EOS implementation bound to the LAMMPS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_lammps_interaction(inter_param))


def get_lammps_file_manifest(model_files, default_manifest):
    """Return EOS-specific transfer file lists."""
    manifest = {key: list(value) for key, value in default_manifest.items()}
    manifest["forward_common_files"] = list(model_files)
    return manifest


def get_lammps_runtime_policy(default_policy):
    """Return EOS-specific runtime policy."""
    policy = dict(default_policy)
    policy["shared_input_file"] = False
    return policy


__all__ = ["EOS", "get_lammps_file_manifest", "get_lammps_runtime_policy"]
