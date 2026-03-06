"""ABACUS-first property registry.

This registry is the ABACUS entrypoint for property dispatch.
It can diverge from other backends as support matrices evolve.
"""

from apex.core.property.abacus.Cohesive import Cohesive
from apex.core.property.abacus.Decohesive import Decohesive
from apex.core.property.abacus.Elastic import Elastic
from apex.core.property.abacus.EOS import EOS
from apex.core.property.abacus.FiniteTlatt import FiniteTlatt
from apex.core.property.abacus.Gamma import Gamma
from apex.core.property.abacus.Interstitial import Interstitial
from apex.core.property.abacus.Phonon import Phonon
from apex.core.property.abacus.Surface import Surface
from apex.core.property.abacus.Vacancy import Vacancy


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
