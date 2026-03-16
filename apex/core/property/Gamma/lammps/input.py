"""Property-local LAMMPS input builders for Gamma."""

from pathlib import Path

from dpdata.periodic_table import Element

from apex.core.calculator.lib.lammps_utils import element_list
from apex.core.calculator.lib.lammps_utils import make_lammps_eval
from apex.core.calculator.lib.lammps_utils import make_lammps_equi


_INPUT_TEMPLATE = Path(__file__).resolve().parent / "in.lammps"
_SETFORCE_VALUES = {"true": "0", "false": "NULL"}


def _render_gamma_setforce(add_fix):
    if not add_fix:
        return ""

    fix_values = []
    for axis in add_fix:
        key = str(axis).lower()
        if key not in _SETFORCE_VALUES:
            raise RuntimeError(
                "Gamma add_fix must contain only true/false-compatible values"
            )
        fix_values.append(_SETFORCE_VALUES[key])
    return "fix             1 all setforce %s\n" % " ".join(fix_values)


def _render_mace_options(model_param):
    if model_param["type"] != "mace":
        return ""
    return "atom_modify map yes\nnewton on\n"


def render_gamma_lammps_input(
    conf, type_map, interaction, model_param, property_param=None
):
    """Render the Gamma-specific LAMMPS input script."""
    property_param = property_param or {}
    cal_type = property_param.get("cal_type", "relaxation")
    if cal_type == "static":
        return make_lammps_eval(conf, type_map, interaction, model_param)
    if cal_type != "relaxation":
        raise RuntimeError(f"unsupported Gamma LAMMPS cal_type: {cal_type}")

    cal_setting = property_param.get("cal_setting", {})
    etol = cal_setting.get("etol", 0)
    ftol = cal_setting.get("ftol", 1e-10)
    maxiter = cal_setting.get("maxiter", 5000)
    maxeval = cal_setting.get("maxeval", 500000)
    add_fix = property_param.get("add_fix")

    if not add_fix:
        relax_pos = cal_setting["relax_pos"]
        relax_shape = cal_setting["relax_shape"]
        relax_vol = cal_setting["relax_vol"]
        if [relax_pos, relax_shape, relax_vol] == [True, False, False]:
            return make_lammps_equi(
                conf,
                type_map,
                interaction,
                model_param,
                etol,
                ftol,
                maxiter,
                maxeval,
                False,
                prop_type=property_param.get("type", "gamma"),
            )
        if [relax_pos, relax_shape, relax_vol] in ([True, True, True], [True, True, False]):
            return make_lammps_equi(
                conf,
                type_map,
                interaction,
                model_param,
                etol,
                ftol,
                maxiter,
                maxeval,
                True,
                prop_type=property_param.get("type", "gamma"),
            )
        if [relax_pos, relax_shape, relax_vol] == [False, False, False]:
            return make_lammps_eval(conf, type_map, interaction, model_param)
        raise RuntimeError("not supported calculation setting for Gamma LAMMPS")

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
        "__SETFORCE_FIX__": _render_gamma_setforce(add_fix),
        "__MINIMIZE__": "minimize        %e %e %d %d\n"
        % (etol, ftol, maxiter, maxeval),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


__all__ = ["render_gamma_lammps_input"]
