"""Helpers for ABACUS backend property wrappers."""


def ensure_interaction(inter_param):
    """Normalize and validate interaction for ABACUS backend properties."""
    inter = dict(inter_param or {})
    if not inter:
        inter["type"] = "abacus"
    if inter.get("type") != "abacus":
        raise RuntimeError("ABACUS property implementation requires interaction.type=abacus")
    return inter
