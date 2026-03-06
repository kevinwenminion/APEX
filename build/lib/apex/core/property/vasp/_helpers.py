"""Helpers for VASP backend property wrappers."""


def ensure_interaction(inter_param):
    """Normalize and validate interaction for VASP backend properties."""
    inter = dict(inter_param or {})
    if not inter:
        inter["type"] = "vasp"
    if inter.get("type") != "vasp":
        raise RuntimeError("VASP property implementation requires interaction.type=vasp")
    return inter
