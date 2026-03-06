"""VASP-first property registry.

This registry is the VASP entrypoint for property dispatch.
It can diverge from other backends as support matrices evolve.
"""

from apex.core.property.vasp.Cohesive import Cohesive
from apex.core.property.vasp.Decohesive import Decohesive
from apex.core.property.vasp.Elastic import Elastic
from apex.core.property.vasp.EOS import EOS
from apex.core.property.vasp.FiniteTlatt import FiniteTlatt
from apex.core.property.vasp.Gamma import Gamma
from apex.core.property.vasp.Interstitial import Interstitial
from apex.core.property.vasp.Phonon import Phonon
from apex.core.property.vasp.Surface import Surface
from apex.core.property.vasp.Vacancy import Vacancy


PROPERTY_CLASS_MAP = {
    "eos": EOS,
    "cohesive": Cohesive,
    "elastic": Elastic,
    "vacancy": Vacancy,
    "interstitial": Interstitial,
    "surface": Surface,
    "gamma": Gamma,
    "phonon": Phonon,
    "decohesive": Decohesive,
    # Kept for backward compatibility; FiniteTlatt itself enforces support.
    "finitetlatt": FiniteTlatt,
}
