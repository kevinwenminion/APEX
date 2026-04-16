# RSS Examples (HEA and HEO)

This folder provides examples for generating random solid
solution (RSS) structures with:

- HEA example: `examples/rss/HEA/`
- HEO example: `examples/rss/HEO/`

Both examples are driven by `apex rss <rss.json>`.

## Quick Start

Run HEA:

```bash
apex rss examples/rss/HEA/rss.json
```

Run HEO:

```bash
apex rss examples/rss/HEO/rss.json
```

Generated structures are written to the output location configured in each
`rss.json` (for example `RSS_HEA/POSCAR` or `RSS_HEO/POSCAR`).

If `metadata` is enabled, an additional `rss_metadata.json` is generated in
the same output directory.

## Example Folder Layout

```text
examples/rss/
├── README.md
├── HEA/
│   ├── rss.json
│   ├── parent/
│   └── RSS_HEA/
└── HEO/
    ├── rss.json
    ├── parent/
    └── RSS_HEO/
```

## Full `rss.json` Key Reference

The following keys are supported by the current implementation in
`apex/rss.py` and `apex/core/lib/rss.py`.

### 1) Structure Input

1. `parent_structure`
- Type: `string`
- Meaning: Relative path (from the `rss.json` directory) to a parent structure,
    typically POSCAR.
- Notes: Provide either `parent_structure` or `parent_lattice`.

2. `parent_lattice`
- Type: `object`
- Meaning: Build the parent structure directly in code (without POSCAR).
- Supported sub-keys:
    - `type`: one of `fcc` / `bcc` / `sc` / `hcp` / `diamond`
    - `element`: initial element symbol, default `Ni`
    - `a`: lattice parameter, default `3.6`
    - `supercell`: internal pre-expansion, e.g. `[5, 5, 5]`

3. `supercell`
- Type: `array[int, int, int]`
- Meaning: Expand the loaded/built parent structure after loading/building.
- Notes: If both `parent_lattice.supercell` and top-level `supercell` are set,
    both expansions are applied.

4. `output_structure`
- Type: `string`
- Meaning: Output structure path (relative to `rss.json`), default `POSCAR`.
- Notes: If `num_configs > 1`, additional structures are named as
    `POSCAR_002`, `POSCAR_003`, etc.

### 2) Composition and Sublattice

5. `compositions`
- Type: `object`
- Meaning: Species fractions on each sublattice; each sublattice must sum to
    `1.0`.
- Modes:
    - Single-sublattice: `{"all": {...}}`
    - Multi-sublattice: e.g. `{"cation": {...}, "anion": {...}}`

For an A/B/O-type sublattice system, define three composition blocks such as
`A`, `B`, and `O`. Put the tunable species on `A` and `B`, and keep `O` fixed
to `1.0` when oxygen should remain fully occupied.

Example:

```json
{
    "compositions": {
        "A": {
            "Mg": 0.5,
            "Co": 0.5
        },
        "B": {
            "Cr": 0.5,
            "Fe": 0.5
        },
        "O": {
            "O": 1.0
        }
    }
}
```

6. `sublattices` (optional)
- Type: `array[object]`
- Meaning: Explicit site-index mapping for each sublattice.
- Item format:
    - `name`: sublattice name (must match keys in `compositions`)
    - `site_indices`: integer list
- Notes: If omitted and top-level `supercell` is provided, the runner tries
    automatic assignment.

7. `allow_vacancies`
- Type: `bool`, default `false`
- Meaning: Allow vacancy-like species aliases (`vac`, `vacancy`, `x`, `none`),
    internally mapped to `X`.

### 3) SRO Targets

8. `sro_targets` (optional)
- Type: `object`
- Meaning: Warren-Cowley SRO target values.
- Format:
    - top-level keys: `shell0`, `shell1`, ... (or `0`, `1`, ...)
    - each shell contains pair targets, e.g. `"Co-Ni": 0.0`
- Notes: If omitted, all pair targets default to `0.0` for all shells, which means generate a random solid solution as closely as the sampler allows.

9. `shell_cutoffs`
- Type: `array[float]`
- Meaning: Neighbor-shell cutoffs (ascending, positive).
- Notes:
    - If omitted, a default first-shell cutoff is inferred from structure.

10. `shell_weights` (optional)
- Type: `array[float]`
- Meaning: Weight of each shell in the objective function.
- Notes: Length must match `shell_cutoffs`; defaults to all `1.0`.

### 4) Sampling and Convergence Control

11. `max_steps`
- Type: `int`, default `20000`
- Meaning: Maximum Monte Carlo swap attempts.

12. `temperature`
- Type: `float`, default `0.05`
- Meaning: Metropolis temperature parameter.

13. `tol`
- Type: `float`, default `1e-3`
- Meaning: Numerical tolerance and near-target criterion.

14. `patience`
- Type: `int | null`, default `null`
- Meaning: Early-stop patience.
- Notes: `null` disables early stopping.

15. `seed` (optional)
- Type: `int`
- Meaning: Random seed for reproducibility.

16. `show_progress`
- Type: `bool`, default `true`
- Meaning: Show tqdm progress bar and live gap metrics.

### 5) Multi-Configuration Output

17. `num_configs`
- Type: `int`, default `1`
- Meaning: Number of structures to output, useful when generate mulitple configurations for average.

18. `interval`
- Type: `int`, default `100`
- Meaning: Sampling interval (in MC steps) for multi-configuration output.

19. `metadata`
- Type: `bool`, default `true`
- Meaning: Write `rss_metadata.json`.

## Minimal HEA-Style Example (No POSCAR)

```json
{
    "parent_lattice": {
        "type": "fcc",
        "element": "Ni",
        "a": 3.6,
        "supercell": [5, 5, 5]
    },
    "compositions": {
        "all": {
            "Co": 0.2,
            "Cr": 0.2,
            "Fe": 0.2,
            "Mn": 0.2,
            "Ni": 0.2
        }
    },
    "shell_cutoffs": [2.8],
    "output_structure": "./RSS_HEA/POSCAR"
}
```
