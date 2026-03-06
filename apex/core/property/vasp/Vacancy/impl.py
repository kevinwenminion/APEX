"""VASP backend implementation entry for Vacancy."""

from apex.core.property.vasp._helpers import ensure_interaction
from .logic import Vacancy as BackendVacancy


class Vacancy(BackendVacancy):
    """Vacancy implementation bound to the VASP backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_interaction(inter_param))
