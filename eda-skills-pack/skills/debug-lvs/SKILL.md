---
name: debug-lvs
description: Debug KLayout LVS mismatches on IHP SG13G2 designs, identify root causes, and suggest fixes
---

# Debug LVS Mismatches (IHP SG13G2)

## When to use

After running LVS and getting mismatches between layout and schematic. This skill helps identify the root cause of each mismatch category and suggests targeted fixes.

## Running LVS

The IHP PDK provides a Python-based LVS runner at `$PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/lvs/run_lvs.py`.

```bash
# Standard run
python3 $PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/lvs/run_lvs.py \
  --layout=design.gds \
  --netlist=design.cdl \
  --topcell=<TOPCELL> \
  --run_mode=flat \
  --verbose

# Netlist extraction only (no comparison)
python3 $PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/lvs/run_lvs.py \
  --layout=design.gds \
  --netlist=design.cdl \
  --net_only

# With simplification disabled (debugging)
python3 $PDK_ROOT/ihp-sg13g2/libs.tech/klayout/tech/lvs/run_lvs.py \
  --layout=design.gds \
  --netlist=design.cdl \
  --no_simplify
```

Output lands in `lvs_run_<timestamp>/`:
- `.log` -- execution report
- `.cir` -- extracted netlist (SPICE)
- `.lvsdb` -- comparison database (open in KLayout Netlist Browser)

## Viewing results

```bash
klayout design.gds
# File -> Load LVS database -> select .lvsdb
# Use Netlist Browser to inspect mismatches
```

The Netlist Browser shows: matched/unmatched devices, matched/unmatched nets, and pin mismatches. Navigate each to locate the issue in layout.

## Recognized devices in IHP SG13G2

### MOSFETs

| LVS name | Type | Gate oxide | VDD | Min L |
|----------|------|-----------|-----|-------|
| sg13_lv_nmos | NMOS | Thin | 1.2V | 0.13 um |
| sg13_lv_pmos | PMOS | Thin | 1.2V | 0.13 um |
| sg13_hv_nmos | NMOS | Thick (ThickGateOx) | 3.3V | 0.45 um |
| sg13_hv_pmos | PMOS | Thick (ThickGateOx) | 3.3V | 0.40 um |

Extracted parameters: W (width), L (gate length). Terminals: S, D, G, B (bulk/well).

### Resistors

| LVS name | Type | Recognition layers |
|----------|------|-------------------|
| rsil | Silicided poly | GatePoly (no SalBlock) |
| rppd | Unsilicided poly (p-doped) | GatePoly + SalBlock + res_drw (24/0) + pSD |
| rhigh | High-resistance poly | GatePoly + SalBlock + res_drw (24/0) + identical pSD/nSD |

### Capacitors

| LVS name | Type | Recognition layers |
|----------|------|-------------------|
| MIM | Metal-Insulator-Metal | mim_drw (36/0) between Metal5 and TopMetal1 |
| S-Varicap | Variable capacitor | varicap_drw (70/0) |

### BJTs (SiGe HBTs)

| LVS name | fT | Emitter length |
|----------|-----|---------------|
| npn13G2 | 350 GHz | Fixed 0.9 um |
| npn13G2L | 350 GHz | 1.0 - 2.5 um |
| npn13G2V | 350 GHz | 1.0 - 5.0 um |

### Other devices

- **Diodes**: standard diodes, antenna diodes (dantenna_n, dantenna_p), Schottky (Schottky_nbl1)
- **ESD devices**: extracted from recog_esd (99/30)
- **Inductors**: ind_drw (27/0)

## Common mismatch categories and fixes

### 1. Dummy transistor mismatches (most common)

**Symptom**: Extra NFET devices in layout that don't exist in schematic. Bodies connected to BN (bulk N).

**Root cause**: GatePoly filler over Active filler is recognized as NFET devices.

**Fix**: Update to latest PDK (post-PR #277) which excludes dummy transistors not connected to Metal1. If using an older version, dummy transistors will appear as unmatched NFETs.

### 2. Hierarchy extraction issues

**Symptom**: Devices appear at the wrong hierarchy level (e.g., antenna diodes extracted at top level instead of sub-cell).

**Root cause**: `dantenna_p` uses pwell as first argument in boolean operations. Since pwell is computed from chip boundary (inherently flat), recognition shapes become flat.

**Fix**: Use `--run_mode=flat` for simpler designs. For hierarchical designs, ensure antenna diode cells are properly structured. Use `blank_circuit` to exclude problematic cells from comparison.

### 3. SRAM macro mismatches

**Symptom**: `RSC_IHPSG13_CDLYX1_DUMMY` uses an "lvsres" resistor that doesn't match the LVS name. Fill-cap cells have pin label mismatches.

**Fix**: Use `blank_circuit` to exclude known-good SRAM cells. Switch to flat mode. SRAM cells pass commercial tool LVS -- this is a KLayout-specific compatibility issue.

### 4. Net name / bracket mismatches

**Symptom**: Layout names like `um_ow[169]` don't match schematic names like `UM_OW73`.

**Root cause**: LVS script removes square brackets from element names.

**Fix**: Avoid brackets in net names. Use consistent naming between schematic and layout. If brackets are unavoidable, patch the LVS reader.

### 5. Unit/scale mismatches

**Symptom**: Device parameter values don't match between layout and schematic.

**Root cause**: SPICE netlist units don't match layout extraction scale.

**Fix**: Add 'U' suffix to netlist dimensions (e.g., `W=10U` instead of `W=10e-6`). Or use `--set_scale` argument.

### 6. "Terminal still connected after removing device" error

**Symptom**: Runtime error during LVS simplification.

**Root cause**: Device removal during simplification leaves dangling terminal connections.

**Fix**: Use `--no_simplify` flag to bypass simplification. Then investigate which device causes the issue.

### 7. Parallel device ambiguity

**Symptom**: Devices with different parameters connected in parallel cause comparison failures.

**Root cause**: The matcher cannot associate parallel devices correctly when they share identical connection signatures but different parameter values.

**Fix**: Add explicit net labels to disambiguate parallel connections. Use `--purge_nets` to remove floating nets.

### 8. Performance / infinite loop on large designs

**Symptom**: LVS hangs or runs indefinitely.

**Root cause**: Large designs with many parallel nets cause exponential matching complexity.

**Fix**: Add net labels aggressively. Use `--purge_nets`. Try `--run_mode=deep` for large designs (but verify correctness with flat mode first on a subset).

## Debugging workflow

1. **Run LVS**: `python3 run_lvs.py --layout=design.gds --netlist=design.cdl --verbose`
2. **Open .lvsdb** in KLayout Netlist Browser
3. **Check comparison summary**: count of matched/unmatched devices and nets
4. **For device count mismatches**:
   - Extra devices in layout? Check for dummy transistors (filler over active), unintended device recognition
   - Missing devices in layout? Check for missing recognition layers, incorrect layer combinations
5. **For net mismatches (shorts)**:
   - Overlapping metal? Missing cuts? Unintended connections through filler?
6. **For net mismatches (opens)**:
   - Missing vias? Broken metal routes? Missing contacts?
7. **For pin mismatches**:
   - Verify text labels on pins match schematic port names exactly (case-sensitive)
8. **Cross-reference**: Compare extracted netlist (.cir) against schematic to pinpoint discrepancy

## Key flags for troubleshooting

| Flag | When to use |
|------|------------|
| `--run_mode=flat` | First attempt; simpler, more reliable |
| `--run_mode=deep` | Large designs; preserves hierarchy |
| `--no_simplify` | When you get "terminal still connected" errors |
| `--no_series_res` | Skip resistor series merging (debug resistor mismatches) |
| `--no_parallel_res` | Skip resistor parallel merging (debug resistor mismatches) |
| `--combine_devices` | Merge identical devices (reduces comparison complexity) |
| `--purge_nets` | Remove floating nets (fixes phantom net mismatches) |
| `--verbose` | Always recommended for debugging -- detailed rule execution log |
| `--net_only` | Extract netlist only, skip comparison (verify extraction before comparing) |

## IHP-specific gotchas

- **LVS after fill**: Fill generation creates dummy transistors. Use latest PDK (post-PR #277).
- **Python 3.12**: KLayout macros may fail with "No module named imp". Use Python 3.11.
- **Layer definitions**: 258 layers defined in `rule_decks/layers_definitions.lvs` -- the authoritative source.
- **Device extraction order**: MOSFETs -> BJTs -> Resistors -> Capacitors -> Diodes -> ESD -> Inductors.
- **No via generator**: Custom vias must be manually verified for correct LVS recognition.
