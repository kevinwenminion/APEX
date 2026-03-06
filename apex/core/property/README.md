# Property Package Layout

This directory is now organized as **packages only** at top level (no standalone property `.py` modules).

## Design

APEX property dispatch is software-first:

1. Select calculator backend (`vasp`, `abacus`, or `lammps` family) in `factory/`.
2. Select property type (`eos`, `elastic`, `phonon`, etc.) from backend registry.

## Directory Structure

- `factory/`: software-first property factory (`make_property_instance`).
- `Property/`: abstract base `Property` class.
- `<PropertyName>/`: shared/top-level property package (`logic.py` + `__init__.py`).
- `vasp/<PropertyName>/`: VASP-bound property implementation package.
- `abacus/<PropertyName>/`: ABACUS-bound property implementation package.
- `lammps/<PropertyName>/`: LAMMPS-bound property implementation package.

Example:

```text
apex/core/property/
  factory/
  Property/
  Phonon/
  vasp/Phonon/
  abacus/Phonon/
  lammps/Phonon/
```

## Conventions

- `__init__.py`: lightweight export surface.
- `logic.py`: property logic implementation.
- `impl.py` (backend folders): backend-bound entry class that validates interaction type and delegates to local logic.

This layout keeps complex properties extensible (extra backend-specific files can be added inside each property folder).
