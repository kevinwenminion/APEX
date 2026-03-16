"""Property-local LAMMPS input builders for Elastic."""

from pathlib import Path

from dpdata.periodic_table import Element

from apex.core.calculator.lib.lammps_utils import element_list
from apex.core.calculator.lib.lammps_utils import make_lammps_equi
from apex.core.calculator.lib.lammps_utils import make_lammps_eval


_INPUT_TEMPLATE = Path(__file__).resolve().parent / "in.lammps"


def _render_mace_options(model_param):
    if model_param["type"] != "mace":
        return ""
    return "atom_modify map yes\nnewton on\n"


def render_elastic_lammps_input(
    conf, type_map, interaction, model_param, property_param=None
):
    """Render the Elastic-specific LAMMPS input script."""
    property_param = property_param or {}
    cal_type = property_param.get("cal_type", "relaxation")
    cal_setting = property_param.get("cal_setting", {})

    if cal_type == "static":
        return make_lammps_eval(conf, type_map, interaction, model_param)
    if cal_type != "relaxation":
        raise RuntimeError(f"unsupported Elastic LAMMPS cal_type: {cal_type}")

    relax_pos = cal_setting.get("relax_pos", True)
    relax_shape = cal_setting.get("relax_shape", False)
    relax_vol = cal_setting.get("relax_vol", False)

    etol = cal_setting.get("etol", 0)
    ftol = cal_setting.get("ftol", 1e-10)
    maxiter = cal_setting.get("maxiter", 5000)
    maxeval = cal_setting.get("maxeval", 500000)

    if [relax_pos, relax_shape, relax_vol] != [True, False, False]:
        if [relax_pos, relax_shape, relax_vol] == [False, False, False]:
            return make_lammps_eval(conf, type_map, interaction, model_param)
        return make_lammps_equi(
            conf,
            type_map,
            interaction,
            model_param,
            etol,
            ftol,
            maxiter,
            maxeval,
            bool(relax_shape or relax_vol),
            prop_type=property_param.get("type", "elastic"),
        )

    type_map_list = element_list(type_map)
    masses = []
    for ii in range(len(type_map)):
        masses.append("mass            %d %.3f" % (ii + 1, Element(type_map_list[ii]).mass))

    template = _INPUT_TEMPLATE.read_text()
    replacements = {
        "__CONF__": conf,
        "__MACE_OPTIONS__": _render_mace_options(model_param),
        "__MASSES__": "\n".join(masses),
        "__INTERACTION__": interaction(model_param).rstrip("\n"),
        "__ETOL__": f"{etol:e}",
        "__FTOL__": f"{ftol:e}",
        "__MAXITER__": str(maxiter),
        "__MAXEVAL__": str(maxeval),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


__all__ = ["render_elastic_lammps_input"]
