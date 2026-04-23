# Property Package Layout

This directory uses a property-first layout. Shared logic is organized by property, and backend-specific bindings are nested under each property package.

## Design

Runtime dispatch is still software-first:

1. `factory.make_property_instance(...)` selects the calculator backend from `interaction.type`.
2. The backend registry selects the property class for `parameters["type"]`.

Source layout is property-first:

1. Shared logic lives in `apex/core/property/<Property>/logic.py`.
2. Backend bindings live in `apex/core/property/<Property>/<software>/`.

This gives one canonical place for property logic and one canonical import path for backend-bound classes.

## Canonical Layout

- `factory/`: property factory used by runtime dispatch.
- `base.py`: abstract base class.
- `<PropertyName>/`: canonical package for a property.
- `<PropertyName>/logic.py`: shared property implementation.
- `<PropertyName>/vasp/`, `<PropertyName>/abacus/`, `<PropertyName>/lammps/`: backend-bound wrappers around the shared implementation.
- `_interaction_helpers.py`: backend interaction validators shared by the property bindings.
- `_registries.py`: canonical backend registries used by the factory, built by auto-discovering `<Property>/<software>/`.

Example:

```text
apex/core/property/
  factory/
  base.py
  _interaction_helpers.py
  _registries.py
  Gamma/
    __init__.py
    logic.py
    vasp/
      __init__.py
    abacus/
      __init__.py
    lammps/
      __init__.py
```

## Import Rules

Use these paths for new code:

- Shared property class: `from apex.core.property.Gamma import Gamma`
- Backend-bound property class: `from apex.core.property.Gamma.vasp import Gamma`
- Another backend-bound class: `from apex.core.property.Phonon.abacus import Phonon`

## Conventions

- `<PropertyName>/__init__.py`: exports the shared property class.
- `<PropertyName>/logic.py`: contains the shared implementation and shared/default hooks.
- `<PropertyName>/<software>/__init__.py`: validates `interaction.type` and owns backend-specific overrides when a backend needs different file handling, task generation, or post-processing.
- `base.py`: defines the shared `Property` abstract base class.
- `_registries.py`: is the only backend registry module used by the factory and auto-registers property backends by directory layout.

## Migration Guidance

When adding or refactoring a property:

1. Put the actual implementation in `<PropertyName>/logic.py`.
2. Put backend-specific behavior in `<PropertyName>/<software>/__init__.py`, usually by overriding shared hooks from `logic.py`.
3. Export the backend class from `<PropertyName>/<software>/__init__.py` using the same class name as the property directory, for example `class Phonon(...)`.
4. Import backend-bound classes via `<PropertyName>/<software>`.
5. Reuse `base.py`, `_interaction_helpers.py`, and `_registries.py` rather than introducing parallel entry layers.
6. Keep shared algorithms in `logic.py`; move only software-specific filesystem and execution details into backend directories.

If the runtime property key is not simply `<PropertyName>.lower()`, the backend module can set `PROPERTY_TYPE = "your_key"` for registry discovery.

When touching existing code, keep imports and new runtime entrypoints on the property-first layout.
