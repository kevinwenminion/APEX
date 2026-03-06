"""LAMMPS backend implementation entry for Phonon."""

from apex.core.property.lammps._helpers import ensure_interaction
from .logic import Phonon as BackendPhonon


class Phonon(BackendPhonon):
    """Phonon implementation bound to the LAMMPS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_interaction(inter_param))
