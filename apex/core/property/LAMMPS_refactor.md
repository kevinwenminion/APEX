# LAMMPS Property Refactor Guide

## Purpose

This document defines the common refactor direction for LAMMPS-backed properties in APEX.

It is intended to answer:

- what should stay in the generic LAMMPS calculator
- what should move into `property/<Prop>/lammps/`
- how new property-specific LAMMPS input logic should be organized
- how future modules from `tial/sma-titanium-aluminide/` should be integrated

This is a framework-level guide. Property-specific details should remain in dedicated documents such as:

- [`FiniteTlatt_refactor.md`](/gauss9/home/cityu/chefan/workspace/research/tial/APEX-1.2.0/apex/core/property/FiniteTlatt_refactor.md)


## Motivation

Historically, APEX placed both generic and property-specific LAMMPS input generation in:

- `apex/core/calculator/lib/lammps_utils.py`

That approach worked initially, but it scales poorly because:

- generic relaxation/static helpers and property-specific templates end up in the same file
- property changes require editing calculator-layer utilities
- backend-specific behavior becomes harder to discover and test

The `FiniteTlatt` refactor was used as the first pilot to establish a cleaner ownership model.


## Scope

This guide only applies to:

- LAMMPS-backed properties

It does not require VASP and ABACUS to use the same physical file structure.

Those backends should follow the same abstraction principles, but not necessarily the same template layout.


## Core Principles

### 1. Keep generic calculator logic generic

The calculator layer should continue to own:

- `POSCAR -> conf.lmp`
- potential/model file linking
- generic file writing and symlink strategy
- generic LAMMPS result parsing
- forward/backward file conventions

It should not own:

- the detailed template of one specific property
- property-specific variable include files
- property-specific postprocessing hooks

### 2. Move property-specific LAMMPS syntax into property backends

If a piece of logic is only meaningful for one property, it should live under:

- `apex/core/property/<Prop>/lammps/`

Examples:

- property-specific `in.lammps`
- property-specific `in.variable`
- property-specific renderer functions
- property-specific task-side input mutations or cleanup

### 3. Prefer native-looking template files over large Python string builders

Python renderers are useful as thin glue, but the actual LAMMPS text should stay visually close to LAMMPS whenever possible.

Preferred pattern:

- `lammps/in.lammps` as a template file
- property-level shared assets such as `in.variable` when appropriate
- small Python renderers that replace placeholders

### 4. Refactor incrementally, not all at once

The migration should proceed property by property.

Do not attempt to rewrite all LAMMPS logic in a single patch.


## Ownership Rules

### Keep in `calculator/lib` or `calculator/Lammps.py`

These belong to the generic LAMMPS backend:

- generic interaction renderers such as:
  - `inter_deepmd`
  - `inter_meam`
  - `inter_meam_spline`
  - `inter_mace`
  - `inter_gap`
- generic input builders such as:
  - `make_lammps_eval`
  - `make_lammps_equi`
  - `make_lammps_press_relax`
- generic dump/log parsing
- generic reconstruction of result dictionaries and `CONTCAR`

### Move into `property/<Prop>/lammps/`

These belong to the property backend:

- property-specific `in.lammps`
- property-specific variable include files
- property-specific rendering logic
- property-specific task-side adjustments after generic input generation
- property-specific LAMMPS-side runtime conventions

### Property-level shared assets

If an asset is tied to one property but may be reused across backend-local helpers, it can live one level above the backend directory, for example:

```text
FiniteTlatt/
  in.variable
  lammps/
    in.lammps
    input.py
    variables.py
```

This is useful when:

- the asset is still property-specific
- but it should not be buried inside one helper sub-layout


## Recommended Directory Pattern

For a LAMMPS-backed property with custom input logic, prefer:

```text
<Prop>/
  lammps/
    __init__.py
    input.py
```

If the property needs a variable include file or shared template asset:

```text
<Prop>/
  in.variable
  lammps/
    __init__.py
    in.lammps
    input.py
    variables.py
```

If the property later grows additional assets:

```text
<Prop>/
  assets/
  in.variable
  lammps/
    __init__.py
    in.lammps
    input.py
    variables.py
```

The goal is not to force one exact tree shape, but to keep ownership obvious and local.


## Rendering Pattern

### Preferred pattern

1. Keep the LAMMPS script as a template file
2. Keep the variable include file as a template file if needed
3. Use thin Python renderers to fill placeholders

For example:

- `lammps/in.lammps`
- `input.py`
- `variables.py`

### Avoid

- very long Python string concatenation blocks for full LAMMPS scripts
- property-specific template bodies inside `lammps_utils.py`
- copying shell `prep/spec` flows directly into the APEX core


## Dispatch Pattern

The calculator should call property-specific renderers through a small dispatch layer rather than embedding property-specific logic inline.

Current acceptable pattern:

- a property-type-to-renderer map in `apex/core/calculator/Lammps.py`
- a property-type-to-file-manifest hook map in `apex/core/calculator/Lammps.py`
- a property-type-to-runtime-policy hook map in `apex/core/calculator/Lammps.py`

This is a reasonable intermediate state.

Longer term, this may evolve into a cleaner backend hook model, but a small registry is enough for now.


## Forward And Backward Files

Each property should clearly define:

- which files must be sent to the remote run
- which files must be collected back

For LAMMPS properties, this usually includes:

- `in.lammps`
- `conf.lmp`
- model file(s)

For properties with extra runtime includes, add them explicitly:

- `in.variable`
- `band.conf`
- other property-specific side inputs

If a property needs a non-default transfer file list, prefer declaring it through a
property-local file manifest hook rather than adding more `if property_type == ...`
branches to the generic calculator.

If a property needs a non-default `in.lammps` sharing strategy, such as task-local
scripts instead of one shared symlinked script, prefer declaring that through a
property-local runtime policy hook.

The backward file list should include whatever the property needs for postprocessing.

Examples:

- standard LAMMPS relaxation:
  - `log.lammps`
  - `dump.relax`
- `FiniteTlatt`:
  - `log.lammps`
  - `dump.relax`
  - `average_box.txt`
- `Phonon`:
  - `outlog`
  - `FORCE_CONSTANTS`


## Result Recovery Chain

LAMMPS property refactors must preserve the postprocessing chain.

### Framework-level chain

1. the dispatcher sends forward files and collects backward files
2. `post_property()` calls `prop.compute(...)`
3. `Property.compute()` iterates over all `task.*`
4. the calculator reconstructs per-task results
5. the property-specific `_compute_lower(...)` aggregates those results into final outputs

Relevant code locations:

- [`common_prop.py`](/gauss9/home/cityu/chefan/workspace/research/tial/APEX-1.2.0/apex/core/common_prop.py)
- [`base.py`](/gauss9/home/cityu/chefan/workspace/research/tial/APEX-1.2.0/apex/core/property/base.py)
- [`Lammps.py`](/gauss9/home/cityu/chefan/workspace/research/tial/APEX-1.2.0/apex/core/calculator/Lammps.py)

### What the generic LAMMPS calculator does

`Lammps.compute()` is responsible for:

- parsing `dump.relax`
- parsing `log.lammps`
- reconstructing cells, coordinates, forces, energies, stresses, virials
- writing `CONTCAR`
- returning a per-task structured result

### What the property layer does

Each property decides how to aggregate the final result.

Examples:

- generic properties may rely mostly on per-task calculator output
- `FiniteTlatt` reads `average_box.txt` to compute averaged lattice parameters

This means:

- template/input refactors must never break the backward file list
- property-specific aggregation logic must remain explicit


## Migration Strategy

### Phase 1: pilot properties

Use a small number of properties to establish the pattern.

Recommended pilot order:

1. `FiniteTlatt`
2. `Phonon`
3. `Gamma`

These are good candidates because they already contain or imply property-specific LAMMPS behavior.

### Current pilot status

- `FiniteTlatt` now uses:
  - property-local `lammps/in.lammps`
  - property-level shared `in.variable`
  - thin Python renderers
- legacy `npt+ave/time` fallback now routes through the property renderer registry in
  `calculator/Lammps.py`
  instead of a `make_lammps_FiniteTlatt(...)` wrapper in `calculator/lib/lammps_utils.py`
- `FiniteTlatt` transfer file lists are now also declared through a property-local
  file manifest hook instead of calculator-side `property_type == "finitetlatt"` branches
- `Phonon` now uses:
  - property-local `lammps/in.lammps`
  - property-local `input.py`
  - property-side runtime generation of `band.conf` and `run_command`
- `Phonon` transfer file lists are now also declared through a property-local
  file manifest hook
- `Gamma` now uses:
  - property-local `lammps/in.lammps`
  - property-local `input.py`
  - property-local rendering of `fix all setforce` when `add_fix` is requested
  - fallback to generic `make_lammps_eval` / `make_lammps_equi` only for non-template cases
- `EOS` now keeps its task-local `in.lammps` behavior through a property-local runtime
  policy hook instead of calculator-side `task_type == "eos"` branches
- `EOS` transfer file lists are now also declared through a property-local
  file manifest hook
- the unused generic-lib wrapper `make_lammps_elastic(...)` has been removed from
  `calculator/lib/lammps_utils.py`; future Elastic-specific input work should land
  under `property/Elastic/lammps/` instead
- `Elastic` now uses:
  - property-local `lammps/in.lammps`
  - property-local `input.py`
  - a property-local renderer for the canonical fixed-cell relaxation path
  - fallback to generic helpers only for non-canonical `cal_setting` combinations
- `Cohesive`, `Decohesive`, `Interstitial`, `Surface`, and `Vacancy` currently remain on
  generic LAMMPS input/runtime behavior and now share one thin generic binding helper
  instead of duplicating identical backend wrapper classes
- these generic properties now also expose property-local structured backend summaries in
  their own `lammps/__init__.py`, so maintainers can see what each property computes,
  what the default run mode is, and which metadata files define task meaning

For `Phonon`, the current LAMMPS scope is intentionally limited to:

- `approach = "linear"`

The displacement workflow remains outside this minimal refactor and should be treated separately if LAMMPS support is expanded later.


## Current Status

### Completed property-local migrations

These properties now have explicit property-local LAMMPS ownership because they need
custom input text, custom runtime conventions, or custom transfer-file rules:

- `FiniteTlatt`
- `Phonon`
- `Gamma`
- `EOS`
- `Elastic`

### Intentionally generic LAMMPS properties

These properties currently differ mainly in structure generation and postprocessing,
not in LAMMPS input syntax or runtime conventions. They therefore remain on generic
LAMMPS input generation for now:

- `Cohesive`
- `Decohesive`
- `Interstitial`
- `Surface`
- `Vacancy`

This is an explicit design choice, not unfinished work.

### Discoverability for generic properties

Even when a property stays on generic LAMMPS input, its `property/<Prop>/lammps/`
module should still explain what that backend binding means.

The current lightweight pattern is:

- keep the runtime/input path generic
- keep the backend binding class local to `property/<Prop>/lammps/__init__.py`
- expose a structured `LAMMPS_BACKEND_SUMMARY` there for maintenance and inspection

This lets maintainers answer:

- what the property computes
- what the default LAMMPS run mode is
- which task/property metadata files carry semantic meaning

The summary can be queried from the factory layer, for example:

```python
from apex.core.property.factory import get_lammps_backend_summary

summary = get_lammps_backend_summary("surface")
```

This pattern is currently used for:

- `Cohesive`
- `Decohesive`
- `Interstitial`
- `Surface`
- `Vacancy`

### Future candidates for deeper review

If later evidence shows that more backend-local LAMMPS behavior is needed, the most
likely candidates to revisit are:

- `Interstitial`
- `Surface`
- `Vacancy`

These are the properties most likely to grow backend-specific conventions if future
domain workflows require them.

### Phase 2: expand only where ownership is clearly property-specific

After pilots are stable, continue with properties that have:

- custom input templates
- custom include files
- custom postprocessing hooks
- custom runtime conventions

Do not migrate generic helpers just for uniformity.

### Phase 3: leave generic helpers where they are unless a stronger abstraction appears

The following should remain generic until there is a strong reason otherwise:

- `make_lammps_eval`
- `make_lammps_equi`
- `make_lammps_press_relax`


## Integration With Future tial Migration

Future migration from:

- `tial/sma-titanium-aluminide`

should follow the same ownership rules.

### What to borrow from tial

- template colocation
- property-local discoverability
- natural grouping of:
  - `in.lammps`
  - include fragments
  - spec-like assets

### What not to copy directly

- shell-driven orchestration as the primary framework interface
- environment-heavy helper stacks
- large-scale text substitution as the main abstraction

### Better integration path

When importing material from tial:

1. migrate the template/resource asset first
2. wrap it with a thin Python renderer
3. integrate it into the property-local LAMMPS backend

This keeps APEX Python-driven while still reusing domain assets.


## Testing Expectations

Each migrated property should be checked at three levels:

1. template rendering
   - placeholders are replaced correctly
   - final `in.lammps` looks structurally correct
2. task preparation
   - required side files are created
   - symlinks and include files are correct
3. smoke postprocessing
   - backward files required by the property are enough to reconstruct final results

In sandboxed environments where repository unit tests cannot write to their original locations, a `/tmp` smoke test is acceptable as an intermediate validation method.

Examples already added during the pilot stage:

- [`tests/test_finitetlatt.py`](/gauss9/home/cityu/chefan/workspace/research/tial/APEX-1.2.0/tests/test_finitetlatt.py)
- [`tests/test_phonon_lammps.py`](/gauss9/home/cityu/chefan/workspace/research/tial/APEX-1.2.0/tests/test_phonon_lammps.py)
- [`tests/test_gamma_lammps.py`](/gauss9/home/cityu/chefan/workspace/research/tial/APEX-1.2.0/tests/test_gamma_lammps.py)
- `/tmp`-backed smoke tests are acceptable for dispatcher/input validation when repository
  fixture directories are not writable in the active sandbox


## Non-Goals

This guide does not propose:

- a full rewrite of the LAMMPS calculator
- immediate unification of VASP, ABACUS, and LAMMPS file structures
- migration of every `make_lammps_*` helper into property directories
- direct adoption of shell `prep/spec` workflows inside APEX core


## Immediate Next Steps

After establishing this guide:

1. keep `FiniteTlatt`, `Phonon`, and `Gamma` as reference implementations
2. remove leftover property-specific compatibility wrappers from generic LAMMPS helpers when touched
3. continue only where property-specific ownership is clear
4. revisit the renderer dispatch layer and property file metadata hooks now that at least three properties share the pattern


## Summary

The common direction is:

- generic LAMMPS functionality stays in the calculator layer
- property-specific LAMMPS templates and hooks move into `property/<Prop>/lammps/`
- template files should look like native LAMMPS whenever possible
- migration should proceed incrementally, property by property
- future tial integration should reuse assets, not copy shell workflows wholesale
