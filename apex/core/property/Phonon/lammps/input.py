"""Property-local LAMMPS input builders for Phonon."""

from pathlib import Path

from dpdata.periodic_table import Element

from apex.core.calculator.lib.lammps_utils import element_list


_INPUT_TEMPLATE = Path(__file__).resolve().parent / "in.lammps"


def render_phonon_lammps_input(
    conf, type_map, interaction, model_param, property_param=None
):
    """Render the minimal phonoLAMMPS-compatible input script."""
    type_map_list = element_list(type_map)
    masses = []
    for ii in range(len(type_map)):
        masses.append("mass            %d %.3f" % (ii + 1, Element(type_map_list[ii]).mass))

    template = _INPUT_TEMPLATE.read_text()
    replacements = {
        "__CONF__": conf,
        "__MASSES__": "\n".join(masses),
        "__INTERACTION__": interaction(model_param).rstrip("\n"),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


__all__ = ["render_phonon_lammps_input"]
