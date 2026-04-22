## 1.2.2 update

- Automatic lattice constant estimation from composition-weighted radii
- Automatic supercell generation from composition tolerance
- Supports B2, L12, L10 sublattice-aware systems
- Shape control:
  - near_cubic
  - xy_equal_z_free (for gamma surface / slab)
- Optional maximum atom budget for automatic supercells
- Automatic Break if relaxation step fail
- Retrive failed output file back(main-logs) from the latest failed steps (Prioritize the Relaxmake)

Environment:

```bash
mamba create -n apex python=3.11
mamba activate apex
pip install -e .
```
