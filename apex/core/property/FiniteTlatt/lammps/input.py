"""Property-local LAMMPS input builders for FiniteTlatt."""

from pathlib import Path

from dpdata.periodic_table import Element

from apex.core.calculator.lib.lammps_utils import element_list


_INPUT_TEMPLATE = Path(__file__).resolve().parent / "in.lammps"


def render_finitetlatt_lammps_input(
    conf, type_map, interaction, model_param, property_param=None
):
    """Render the FiniteTlatt-specific LAMMPS input script."""
    type_map_list = element_list(type_map)
    dump_step = 100
    masses = []
    for ii in range(len(type_map)):
        masses.append("mass            %d %.3f" % (ii + 1, Element(type_map_list[ii]).mass))
    interaction_block = interaction(model_param).rstrip("\n")

    template = _INPUT_TEMPLATE.read_text()
    replacements = {
        "__CONF__": conf,
        "__MASSES__": "\n".join(masses),
        "__INTERACTION__": interaction_block,
        "__DUMP_STEP__": str(dump_step),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


__all__ = ["render_finitetlatt_lammps_input"]
