"""ABACUS backend implementation entry for Cohesive."""

from apex.core.property.abacus._helpers import ensure_interaction
from .logic import Cohesive as BackendCohesive


class Cohesive(BackendCohesive):
    """Cohesive implementation bound to the ABACUS backend."""

    def __init__(self, parameter, inter_param=None):
        super().__init__(parameter, ensure_interaction(inter_param))
