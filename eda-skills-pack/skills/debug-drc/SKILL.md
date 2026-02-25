---
name: debug-drc
description: Debug KLayout DRC violations on IHP SG13G2 designs, distinguishing real errors from false positives
---

# Debug DRC Violations (IHP SG13G2)

## When to use

After running DRC on a GDS file and getting violations that need triage. This skill helps identify which violations are real design errors vs known false positives, and suggests fixes for common issues.

## Running DRC

The IHP PDK provides a Python-based DRC runner at `$PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py`.

```bash
# Standard run (recommended first pass -- skip density and extra rules)
python3 $PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py \
  --path=design.gds \
  --topcell=<TOPCELL> \
  --run_mode=deep \
  --no_density \
  --disable_extra_rules \
  --mp=4

# Full run (for tape-out readiness)
python3 $PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py \
  --path=design.gds \
  --topcell=<TOPCELL> \
  --run_mode=deep \
  --antenna \
  --mp=4

# Density-only check (run separately -- slow)
python3 $PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/drc/run_drc.py \
  --path=design.gds \
  --density_only
```

Output lands in `drc_run_<date>_<time>/`:
- `.log` -- execution log
- `.lyrdb` -- KLayout marker database (open with `klayout design.gds -m result.lyrdb`)

## Three rule categories

1. **PreCheck**: Essential tape-out rules. Thoroughly verified. This is what IHP's automated GitHub Actions run on MPW submissions.
2. **Main**: PreCheck + additional rules. The standard full-check deck.
3. **Extra**: Unverified, possibly slow rules. Disable with `--disable_extra_rules` unless specifically investigating.

## Known false positives and safe-to-ignore patterns

### OffGrid violations on filler/block layers
Violations like `OffGrid.XXXXX_nofill` or `OffGrid.XXXXX_block` on layers used only for fill can be ignored -- those layers are not for manufacturing. But OffGrid errors on drawing layers (e.g., `Metal1`, `Activ`, `GatPoly`) are real and mean geometry is not on the 0.005 um manufacturing grid.

**Fix for real offgrid**: If using GDSFactory or scripted layout, set precision to `0.005e-6`.

### Filler density violations (AFil, GFil)
Active filler and GatePoly filler density rules are frequently flagged. The `generate_fill.py` tool is work-in-progress. Common violations:
- `AFil.g` / `AFil.g1`: Active density out of 35-55% range
- `GFil.d`: GatePoly filler space to Active < 1.1 um
- `GFil.g`: GatePoly density below 15%

These are real but may need fill generation tooling to fix. Not a design error.

### Magic overlap warnings (in LibreLane flows)
`Checker.IllegalOverlap` is nullified by default in LibreLane config because Magic reports false-positive overlaps. If running standalone DRC, these can be ignored for IHP designs.

### Extra rules false positives
Rules in the "Extra" category are unverified. Always use `--disable_extra_rules` for production checks.

## Common real violations and fixes

### FEOL (Front-End-Of-Line)

| Rule | Description | Min value | Common cause |
|------|-------------|-----------|--------------|
| Act.a | Active width | 0.15 um | Undersized diffusion |
| Act.b | Active space | 0.21 um | Devices too close |
| Gat.a | GatePoly width | 0.13 um (LV) | Below minimum L |
| Gat.a3 | GatePoly width for 3.3V NFET | 0.45 um | Using LV gate length for HV device |
| Gat.a4 | GatePoly width for 3.3V PFET | 0.40 um | Using LV gate length for HV device |
| Gat.c | GatePoly end cap over Active | 0.18 um | Gate extension too short |
| Cnt.f | Contact-on-Active to GatePoly | 0.11 um | Contact placed too close to gate |
| Cnt.j | Contact on GatePoly over Active | FORBIDDEN | Never place contact on gate over active region |
| NW.b1 | PWell width between NWell regions | 1.8 um | NWells too close -- need 1.8 um P-substrate gap |
| TGO.a | ThickGateOx extension over Active | 0.27 um | ThickGateOx marking not covering enough |
| LU.a | P+Active to nSD-NWell tie distance | max 20 um | Missing substrate/well ties (latch-up) |

### BEOL (Back-End-Of-Line)

| Rule | Description | Min value | Common cause |
|------|-------------|-----------|--------------|
| M1.a / M1.b | Metal1 width / space | 0.16 / 0.18 um | Routing too narrow or too close |
| M2-M5.a / M2-M5.b | Metal2-5 width / space | 0.20 / 0.21 um | Same |
| TM1.a / TM1.b | TopMetal1 width / space | 1.64 / 1.64 um | Thick metal rules -- much wider minimums |
| TM2.a / TM2.b | TopMetal2 width / space | 2.0 / 2.0 um | Same |
| Slit rules | Metal > 30 um needs slits | slit width 2.8-20 um | Wide power straps without slotting |

### Density rules

| Rule | Layer | Min global | Max global |
|------|-------|-----------|-----------|
| M1.j/k | Metal1 | 35% | 60% |
| M2-M5.j/k | Metal2-5 | 35% | 60% |
| TM1.j/k | TopMetal1 | 25% | 70% |
| TM2.j/k | TopMetal2 | 25% | 70% |

### Latch-up rules
- LU.a: Max distance from P+Active to nSD-NWell tie = 20 um. Fix: add substrate ties within 20 um of every PMOS.
- The IHP PDK has no dedicated tap cells. You must manually place substrate/NWell ties.

## Debugging workflow

1. Run DRC with `--disable_extra_rules --no_density` first (fast pass)
2. Open results in KLayout: `klayout design.gds -m result.lyrdb`
3. Use Marker Browser to navigate violations
4. Categorize: offgrid? density? spacing? width? forbidden structure?
5. Check if violation is on a filler/block layer (likely false positive) or drawing layer (likely real)
6. For density violations, run `--density_only` separately after fixing design errors
7. For antenna violations, run with `--antenna` flag (not included in default run)

## IHP-specific gotchas

- **No tapcells in PDK**: Unlike Sky130, there are no pre-built substrate tap cells. You must manually create P+Active ties in P-substrate (connected to VSS) and N+Active ties in NWell (connected to VDD). Guard rings are also manual.
- **No via generator**: No parametric via array generator in current PDK. Manual via placement required.
- **Manufacturing grid**: 0.005 um (5 nm). All geometry vertices must be on-grid.
- **Python 3.12 compatibility**: KLayout macros may fail with "No module named imp". Use Python 3.11 if you hit this.
- **Forbidden structures**: BiWind, PEmWind, BasPoly, DeepCo, PEmPoly, EmPoly, LDMOS, PBiWind, ColWind are all forbidden in the open-source PDK.
- **LVS after fill**: Fill generation can create dummy transistors recognized by LVS. Use latest PDK (post-PR #277) which excludes dummies not connected to Metal1.
