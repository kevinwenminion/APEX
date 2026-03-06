"""LAMMPS-first property registry.

This registry is the LAMMPS entrypoint for property dispatch.
It can diverge from other backends as support matrices evolve.
"""

from apex.core.property.lammps.Cohesive import Cohesive
from apex.core.property.lammps.Decohesive import Decohesive
from apex.core.property.lammps.Elastic import Elastic
from apex.core.property.lammps.EOS import EOS
from apex.core.property.lammps.FiniteTlatt import FiniteTlatt
from apex.core.property.lammps.Gamma import Gamma
from apex.core.property.lammps.Interstitial import Interstitial
from apex.core.property.lammps.Phonon import Phonon
from apex.core.property.lammps.Surface import Surface
from apex.core.property.lammps.Vacancy import Vacancy


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
    "finitetlatt": FiniteTlatt,
}
