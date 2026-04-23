"""Property-local variable file builders for FiniteTlatt."""

from pathlib import Path


_VARIABLE_TEMPLATE = Path(__file__).resolve().parent.parent / "in.variable"


def render_finitetlatt_variable_file(temp, supercell_size, cal_setting):
    """Render the FiniteTlatt-specific LAMMPS variable include file."""
    template = _VARIABLE_TEMPLATE.read_text()
    replacements = {
        "__TEMPERATURE__": f"{temp:.2f}",
        "__NX__": str(supercell_size[0]),
        "__NY__": str(supercell_size[1]),
        "__NZ__": str(supercell_size[2]),
        "__EQUI_STEP__": str(cal_setting["equi_step"]),
        "__N_EVERY__": str(cal_setting["N_every"]),
        "__N_REPEAT__": str(cal_setting["N_repeat"]),
        "__N_FREQ__": str(cal_setting["N_freq"]),
        "__AVE_STEP__": str(cal_setting["ave_step"]),
        "__TIMESTEP__": str(cal_setting["timestep"]),
        "__TDAMP__": str(cal_setting["tdamp"]),
        "__PDAMP__": str(cal_setting["pdamp"]),
    }
    for key, value in replacements.items():
        template = template.replace(key, value)
    return template


__all__ = ["render_finitetlatt_variable_file"]
