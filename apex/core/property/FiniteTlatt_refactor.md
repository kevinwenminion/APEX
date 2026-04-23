# FiniteTlatt LAMMPS Input Refactor Design

## Background

The current `FiniteTlatt` LAMMPS input generation logic is split across two layers:

- `apex/core/property/FiniteTlatt/logic.py`
  - creates `task.*`
  - writes `POSCAR`, `FiniteTlatt.json`, and `in.variable`
- `apex/core/calculator/lib/lammps_utils.py`
  - defines `make_lammps_FiniteTlatt(...)`
  - assembles the full `in.lammps`
- `apex/core/calculator/Lammps.py`
  - dispatches to `make_lammps_FiniteTlatt(...)` in `make_input_file()` when `cal_type == "npt+ave/time"`

This splits the `FiniteTlatt` domain logic into two halves:

- parameters and task orchestration live in the property layer
- the final input template lives in the calculator/lib layer

As a result:

- modifying `FiniteTlatt` requires jumping across several directories
- `lammps_utils.py` mixes generic templates and property-specific templates
- `Lammps.make_input_file()` contains property-specific hardcoded branching
- `FiniteTlatt/logic.py` still orchestrates task creation, but the LAMMPS-specific variable file renderer should live under `FiniteTlatt/lammps/`


## Goals

The refactor should satisfy the following goals:

1. Move the `FiniteTlatt`-specific LAMMPS input template into `FiniteTlatt/lammps/`
2. Keep `calculator/Lammps.py` as a generic driver instead of a growing host for property-specific branches
3. Preserve the current APEX workflow model: property creates tasks, calculator creates potential files and input files
4. Create a reusable extension point for future property-specific LAMMPS templates


## Current Issues

### 1. The responsibility boundary is unnatural

`make_lammps_FiniteTlatt(...)` clearly serves only `FiniteTlatt`, but it currently lives in the generic utility module `lammps_utils.py`.

The variable include file `in.variable` is also backend-specific because it contains native LAMMPS `variable ... equal ...` syntax.

By contrast, the repository already keeps some property-specific LAMMPS behavior in property backend directories, for example:

- `Gamma/lammps/__init__.py`
- `Phonon/lammps/__init__.py`

That already points toward the direction of letting property backends own their LAMMPS-specific behavior.

### 2. The extension point sits in the wrong layer

Current dispatch logic lives in `Lammps.make_input_file()`:

- `relaxation` -> `make_lammps_equi`
- `static` -> `make_lammps_eval`
- `npt+ave/time` -> `make_lammps_FiniteTlatt`

That means every new property-specific input template would require another calculator-layer branch.

### 3. `lammps_utils.py` mixes two kinds of templates

`lammps_utils.py` currently contains:

- generic templates
  - `make_lammps_eval`
  - `make_lammps_equi`
  - `make_lammps_press_relax`
- property-specific templates
  - `make_lammps_FiniteTlatt`
  - arguably `make_lammps_phonon` is close to this category as well

This mixing will keep growing the file and make it harder to tell which functions are reusable and which belong to a single property.


## Reference Implementation Analysis

Reference directory:

- `/gauss9/home/cityu/chefan/workspace/research/tial/sma-titanium-aluminide/src/lammps/calc/lattice_parameter_finite_T`

Its organization is roughly:

- `run.sh prep spec_xxx`
  - reads `spec`
  - copies `in.lammps`, `init.mod`, `potential.mod`
  - generates final inputs by replacing placeholders
- templates are colocated in one directory
  - `in.lammps`
  - `init.mod`
  - `potential.mod`
  - `spec*`

### What is more natural about this implementation

It has several strong points:

1. All files for one calculation type live in one directory
   - templates, spec files, prep scripts, and plotting scripts are naturally grouped
2. The input generation flow is easy to follow
   - `prep` is simply "copy templates and replace variables"
3. The domain meaning is concentrated
   - someone working on finite-temperature lattice parameters can find everything in one place

These are worth borrowing.

### What should not be copied directly

It also has characteristics that do not fit APEX directly:

1. It is a script-driven workflow, not a unified property/calculator abstraction
   - APEX already has `Property`, `Task`, and `Calculator` as framework-level abstractions
2. It depends heavily on shell environment and an external template ecosystem
   - `config`
   - `lmp_pot_spec`
   - `replace_lmp_infile_variable`
   - `change_lmp_infile`
   - `generate_jobfile`
3. It is primarily text-substitution-driven rather than using structured Python interfaces
   - good for flexible one-off experiments
   - weaker for framework-level maintenance and testing

So the conclusion is not "copy `run.sh prep spec` directly", but rather "borrow its directory ownership and template colocation ideas".


## Recommended Approach

A balanced approach is recommended:

- borrow the "templates belong to the property" organization from the reference implementation
- preserve APEX's Python-based orchestration and calculator framework

### Core idea

Move the `FiniteTlatt` LAMMPS input template to:

- `apex/core/property/FiniteTlatt/lammps/input.py`

Suggested interface:

```python
def render_finitetlatt_lammps_input(conf, type_map, interaction, model_param) -> str:
    ...
```

If the logic grows later, it can evolve into:

- `input.py`
- `variables.py`
- `in.lammps`
- property-level shared template assets

### Responsibilities kept in the calculator layer

`apex/core/calculator/Lammps.py` should still handle:

- `POSCAR -> conf.lmp`
- potential file preparation
- writing `inter.json` and `task.json`
- writing the final `in.lammps`

But it should no longer own the `FiniteTlatt` template details.

### Responsibilities added to the property backend layer

`FiniteTlatt/lammps/` should own:

- generation of the `FiniteTlatt`-specific `in.lammps`
- the backend-local rendering logic for the variable include file
- any future `FiniteTlatt`-specific hooks or postprocessing

The variable template itself may live one level higher under `FiniteTlatt/` if it is intended to be shared as a property-level asset.


## Template Readability

The first landed version of `input.py` used Python string assembly to render the LAMMPS script.

That was acceptable for the first minimal refactor because:

- it keeps the change small
- it preserves behavior closely
- it avoids introducing a second refactor axis at the same time

However, it is not the most readable long-term form, so the next cleanup should shift toward template files.

### Why Python string assembly is not ideal

- the visual shape no longer matches the final LAMMPS file closely
- long multi-line command blocks are harder to scan than a native `.lammps` template
- small formatting edits become noisy Python edits
- it is harder for domain users to compare against existing LAMMPS scripts from other projects

### Recommended next step after the current pilot

Once the minimal refactor is stable, the next cleanup should be:

- keep the variable-file renderer in `FiniteTlatt/lammps/`
- replace Python-heavy string assembly with lightweight template files

Suggested target shape:

```text
FiniteTlatt/
  in.variable
  lammps/
    __init__.py
    input.py
    variables.py
    in.lammps
```

In that form:

- `lammps/in.lammps` stays visually close to native LAMMPS syntax
- `FiniteTlatt/in.variable` stays available as a property-level shared template asset
- `input.py` and `variables.py` become thin renderers instead of large string builders

### Recommendation

Recommended current state:

- keep the main orchestration in `logic.py`
- keep the main script template inside `FiniteTlatt/lammps/`
- keep the variable template at the property level when shared access is useful
- prefer template files over long Python string builders


## Recommended Interface Design

The calculator should not directly hardcode imports of one specific property module and one specific function name. A backend hook is a cleaner direction.

### Option A: provide a hook on the property backend class

For example, add to the backend class in `FiniteTlatt/lammps/__init__.py`:

```python
def render_lammps_input(self, conf, type_map, interaction, model_param):
    ...
```

and let higher-level logic call it at the right point.

Pros:

- clearest ownership
- semantically aligned with the property backend
- easy to extend to other properties later

Cons:

- requires a cleaner boundary between property instances and calculator instances

### Option B: provide a module-level renderer in the property backend

For example:

```python
from apex.core.property.FiniteTlatt.lammps.input import render_finitetlatt_lammps_input
```

and let a small registry dispatch to it.

Pros:

- smaller change
- easier to land incrementally

Cons:

- still needs a registry or dispatch map
- less uniform than an object-oriented hook

### Recommendation

Use Option B first, then evolve to Option A if needed later.

Reasons:

- smaller invasion into the current codebase
- enough to complete the first step of moving the template out of `lammps_utils.py`
- later hook extraction will not affect template ownership


## Suggested Directory Layout

Suggested `FiniteTlatt/lammps/` structure:

```text
FiniteTlatt/
  lammps/
    __init__.py
    input.py
```

Where:

- `__init__.py`
  - keeps the backend class
  - may export module-level helpers
- `input.py`
  - is only responsible for generating the `FiniteTlatt` LAMMPS input text

If the logic grows, it may later expand to:

```text
FiniteTlatt/
  lammps/
    __init__.py
    input.py
    variables.py
    templates/
      in_finitetlatt.lammps
```

There is no need to overdesign that in the first step.


## Migration Steps

### Phase 1: move template ownership

1. add `FiniteTlatt/lammps/input.py`
2. migrate `make_lammps_FiniteTlatt(...)` into `render_finitetlatt_lammps_input(...)`
3. keep a compatibility wrapper in `lammps_utils.py` that delegates to the new function
4. after tests pass, remove the old implementation body

The goal of this phase is to fix code ownership without changing the overall interface too much.

### Phase 2: remove calculator-layer hardcoding

1. add a small property-type-to-renderer registry in the calculator layer
2. move the `FiniteTlatt`-specific `cal_type == "npt+ave/time"` dispatch into that registry path
3. keep `make_lammps_eval` and `make_lammps_equi` as truly generic templates

The goal of this phase is to stop using `Lammps.py` conditionals as the place that decides which property template gets used.

### Phase 3: unify property-specific LAMMPS extension points

Later candidates to review:

- `Phonon`
- `Gamma`
- other properties with backend-specific logic

The desired end state is:

- generic templates stay in `calculator/lib`
- property-specific templates and hooks stay in `property/<Prop>/lammps/`


## Scope Of This Round

This implementation round should stay minimal and verifiable. It is not a rewrite of the full LAMMPS calculator.

### In scope for this round

1. update this document and make the staged strategy explicit
2. perform a minimal refactor only for `FiniteTlatt`
3. move `make_lammps_FiniteTlatt(...)` into `FiniteTlatt/lammps/input.py`
4. add a minimal renderer dispatch entry in `Lammps.py`
5. keep a compatibility wrapper to avoid breaking old call paths immediately

### Out of scope for this round

1. do not migrate `make_lammps_eval`
2. do not migrate `make_lammps_equi`
3. do not migrate `make_lammps_press_relax`
4. do not convert all LAMMPS properties to the new pattern at once
5. do not change the overall VASP / ABACUS input organization
6. do not mix this first pilot with broad refactors of other properties

### Suggested rollout order after this round

After `FiniteTlatt` is complete as a pilot, continue only with clearly property-specific LAMMPS logic. Suggested order:

1. `Phonon`
2. `Gamma`
3. other LAMMPS properties that truly contain property-specific input templates or postprocessing

The following should remain in `calculator/lib` for now:

- generic relaxation templates
- generic static/eval templates
- LAMMPS helper utilities that are not property-specific


## Multi-Backend Strategy

APEX supports more than LAMMPS:

- VASP
- ABACUS

So this refactor should not be framed as a `FiniteTlatt` one-off only. It should also consider whether a broader backend pattern is being created.

### Should VASP and ABACUS be refactored in exactly the same way

No. It is not a good idea to force all three backends into exactly the same physical structure.

A better principle is:

1. unify the abstraction boundary
2. do not force identical internal implementations

In other words:

- external extension points should look consistent
- internal organization should stay natural for each backend

### Why identical treatment would be wrong

The three backends are different in character:

- LAMMPS
  - input is usually script-template-based
  - property-specific input variation is large
  - very suitable for property/backend-local template ownership
- VASP
  - mainly `INCAR` / `KPOINTS` / `POTCAR`
  - usually parameter composition rather than full script templates
  - better viewed as structured parameter rendering
- ABACUS
  - mainly `INPUT` / `KPT` / `STRU`
  - also closer to parameter and structure file composition
  - usually has lower density of property-specific full templates than LAMMPS

Therefore:

- LAMMPS is a good candidate for moving templates into `property/<Prop>/lammps/`
- VASP and ABACUS are better handled by keeping generic calculator logic and only adding backend hooks where complexity truly requires it

### Recommended unification target

What should be unified is the interface, not the file shape.

For example, future conceptual extension points may look like:

- `prepare_backend_inputs(...)`
- `render_backend_input(...)`
- `post_process_backend_inputs(...)`

But the concrete output may differ:

- LAMMPS: returns full `in.lammps` text
- VASP: returns `Incar` / `Kpoints` modifications
- ABACUS: returns `INPUT` overrides and `STRU/KPT` adjustments

### Concrete recommendation for VASP and ABACUS

Short term, do not refactor VASP and ABACUS into a LAMMPS-style template-file system just for superficial consistency.

A better approach is:

1. keep the current generic calculator-layer input generation
2. only move logic into `property/<Prop>/<backend>/` when a property develops clearly backend-specific complexity
3. gradually form a consistent hook model instead of performing a large physical migration up front

In practice:

- LAMMPS can move first
- VASP and ABACUS can follow the abstraction later without immediate physical relocation


## Designing For Future tial Module Migration

You may later migrate modules from `tial/sma-titanium-aluminide/` into APEX. That should influence the design now.

Without a clean boundary, two failure modes are likely:

- more and more script logic gets pushed into `calculator/lib`
- or the external project gets copied in wholesale, creating a second parallel system inside APEX

Neither is desirable.

### Migration goals

Migration should try to achieve:

1. preserve the domain knowledge and template assets from the original modules
2. avoid importing the shell workflow unchanged into the APEX core layer
3. make migration happen as resource integration, not as framework duplication

### Recommended migration units

Content migrated later from tial should be separated into three categories:

1. domain assets
   - `in.lammps`
   - `init.mod`
   - `potential.mod`
   - `spec`
   - other template fragments or reference data
2. rendering logic
   - translate `spec`, placeholder replacement, and variable assembly into Python functions
3. execution / postprocessing logic
   - integrate the reusable parts into APEX
   - keep highly experimental shell flows out of the core path for now

### Recommended directory strategy

To make future migration easier, reserve an asset directory under the property backend now, for example:

```text
FiniteTlatt/
  lammps/
    __init__.py
    input.py
    assets/
      templates/
      modules/
      specs/
```

Important:

- `assets/` is not for copying the shell workflow immediately
- it is for giving future tial templates, fragments, and reference specs a natural home

That avoids pushing future migrated content into:

- `calculator/lib`
- top-level `examples/`
- random script directories

### Recommended normalization layer

If `spec`-style configuration needs to be migrated later, APEX should not continue to rely on shell text replacement directly.

A Python normalization layer is a better target, for example:

```python
class FiniteTlattCase:
    potential_id: str
    atom_type: str
    structure: str
    temperature: float
    supercell: tuple[int, int, int]
    thermostat: str
    ...
```

This normalized object can then absorb:

- native APEX parameters
- parameters read from future `spec` files

and hand them to the renderer in a single shape.

Benefits:

- old `spec` content can be supported incrementally
- the native APEX parameter model does not get polluted by old shell variable conventions
- tests can target Python objects directly instead of running the full shell prep flow

### Recommended compatibility path

If some tial modules need to be migrated quickly later, use a two-step strategy:

1. migrate resources first
   - move templates, fragments, and reference specs into `assets/`
2. translate logic second
   - first add a minimal Python wrapper
   - then gradually replace shell placeholder logic

Do not attempt a full shell workflow port in one step. That is the easiest way to carry unnecessary environment coupling into APEX.


## Suggested Unified Architecture

Combining the multi-backend requirement and future migration needs, the long-term target should be:

### 1. property logic

Responsible for:

- task lists
- structure preparation
- result interpretation

Not responsible for:

- software-specific input file details

### 2. backend adapter

Located in:

- `property/<Prop>/lammps/`
- `property/<Prop>/vasp/`
- `property/<Prop>/abacus/`

Responsible for:

- property-specific rendering for one software backend
- backend-specific pre/post hooks

### 3. calculator

Responsible for:

- generic file writing
- potential / pseudopotential preparation
- generic linking strategy
- forward/backward file-set conventions

Not responsible for:

- the detailed template of one specific property

### 4. assets

Responsible for:

- future migrated templates, fragments, reference specs, and helper modules from tial

This provides the main benefits:

- LAMMPS can naturally absorb template-heavy migrated content
- VASP and ABACUS do not get forced into unnecessary templateization
- future tial imports do not require undoing this refactor later


## Should The `prep/spec` Logic Be Referenced

Conclusion:

- yes, its "keep templates close to the property" organization is worth borrowing
- no, its shell `prep/spec` workflow should not be copied directly

### What to borrow

- a property's template files should live as close as possible to that property
- input templates, variable templates, and property-specific postprocessing should converge in one backend directory
- preparing inputs should ideally look like template rendering rather than scattered string concatenation across unrelated layers

### What not to copy directly

- a shell-driven prepare flow
- large-scale placeholder-replacement-driven input generation
- heavy dependence on external environment scripts and directory conventions

The better APEX-style version is:

- keep Python as the orchestrator
- move input generation responsibility from `calculator/lib/lammps_utils.py` into `FiniteTlatt/lammps/`
- if template complexity grows later, consider lightweight template files then, rather than switching to a shell replacement system now


## Recommended Implementation Cut

If only one minimal but effective refactor is performed now, the recommended scope is:

1. move `make_lammps_FiniteTlatt` into `FiniteTlatt/lammps/input.py`
2. have `Lammps.py` call it through a very small registry
3. allow the property layer to call backend-local helpers to generate `in.variable`
4. do not change `common_prop.py`, the `Property` abstraction, or the workflow layer yet

This gives the main benefits with limited risk:

- ownership becomes clearer
- the maintenance entry point for `FiniteTlatt` becomes more concentrated
- it creates a clean path for later extraction of a general property-specific LAMMPS renderer model
- it keeps the property layer focused on orchestration while the backend layer owns the LAMMPS syntax


## Non-Goals

This refactor should not try to do the following at the same time:

- rewrite the full LAMMPS calculator abstraction
- migrate all `make_lammps_*` functions at once
- replace Python generation logic with shell `prep/spec`
- introduce a heavy template engine

That would expand a code-ownership cleanup into a framework rewrite.


## Final Recommendation

The final recommendation is:

- `make_lammps_FiniteTlatt(...)` should move into `FiniteTlatt/lammps/` based on ownership
- the `lattice_parameter_finite_T` reference implementation is more natural in terms of organization
- but only its template colocation and discoverability ideas should be borrowed, not its shell workflow directly
- the best path is a balanced refactor: keep Python orchestration, let the property backend own the property-specific input template
