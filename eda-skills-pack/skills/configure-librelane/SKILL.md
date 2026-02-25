---
name: configure-librelane
description: Configure LibreLane RTL-to-GDS flow for IHP SG13G2 designs, from minimal to full-chip
---

# Configure LibreLane Flow (IHP SG13G2)

## When to use

When setting up a new LibreLane project for IHP SG13G2 or tuning an existing configuration. Covers config.json structure, parameter selection, and common patterns from production testcases.

## Config format

LibreLane uses JSON config files (version 2), not YAML. The config supports PDK-conditional sections.

```json
{
  "meta": {
    "version": 2
  },
  "DESIGN_NAME": "my_design",
  "VERILOG_FILES": "dir::src/*.v",
  "CLOCK_PORT": "clk",
  "CLOCK_NET": "clk",
  "CLOCK_PERIOD": 25,
  "pdk::ihp-sg13g2*": {
    "CLOCK_PERIOD": 25,
    "FP_CORE_UTIL": 35,
    "DIODE_CELL": "sg13g2_antennanp/A",
    "RUN_HEURISTIC_DIODE_INSERTION": 1,
    "HEURISTIC_ANTENNA_THRESHOLD": 110
  }
}
```

## Invocation

```bash
# Standard run via nix
librelane-nix --pdk-root $PDK_ROOT --pdk ihp-sg13g2 --scl sg13g2_stdcell --condensed config.json

# Via Makefile (if project provides one)
make librelane

# View results
make librelane-openroad    # OpenROAD GUI
make librelane-klayout     # KLayout
```

## Minimal config (combinational / small designs)

```json
{
  "meta": { "version": 2 },
  "DESIGN_NAME": "inverter",
  "VERILOG_FILES": "dir::src/inverter.v",
  "pdk::ihp-sg13g2*": {
    "FP_SIZING": "absolute",
    "DIE_AREA": "0 0 50 50",
    "FP_PDN_VPITCH": 25,
    "FP_PDN_HPITCH": 25,
    "FP_PDN_VOFFSET": 5,
    "FP_PDN_HOFFSET": 5,
    "PL_TARGET_DENSITY_PCT": 75
  }
}
```

## Standard core-only config (moderate complexity)

```json
{
  "meta": { "version": 2 },
  "DESIGN_NAME": "y_huff",
  "VERILOG_FILES": "dir::src/*.v",
  "CLOCK_PORT": "clk",
  "CLOCK_NET": "clk",
  "CLOCK_PERIOD": 18,
  "pdk::ihp-sg13g2*": {
    "CLOCK_PERIOD": 18,
    "FP_SIZING": "absolute",
    "DIE_AREA": "0 0 700 700",
    "FP_CORE_UTIL": 35,
    "PL_TARGET_DENSITY_PCT": 45,
    "DIODE_CELL": "sg13g2_antennanp/A",
    "RUN_HEURISTIC_DIODE_INSERTION": 1,
    "HEURISTIC_ANTENNA_THRESHOLD": 110,
    "RUN_ANTENNA_REPAIR": 1,
    "PL_RESIZER_SETUP_SLACK_MARGIN": 0.2,
    "PL_RESIZER_HOLD_SLACK_MARGIN": 0.2,
    "GRT_RESIZER_SETUP_SLACK_MARGIN": 0.2,
    "GRT_RESIZER_HOLD_SLACK_MARGIN": 0.2,
    "SYNTH_MAX_FANOUT": 4
  }
}
```

## Full-chip config (with IO pads, LibreLane Chip flow)

```json
{
  "meta": {
    "version": 3,
    "flow": "Chip",
    "substituting_steps": {
      "Checker.IllegalOverlap": null
    }
  },
  "DESIGN_NAME": "chip_top",
  "VERILOG_FILES": [
    "dir::../src/chip_top.sv",
    "dir::../src/chip_core.sv"
  ],
  "CLOCK_PORT": "clk_PAD",
  "CLOCK_NET": "clk_pad/p2c",
  "CLOCK_PERIOD": 20,
  "VDD_NETS": ["VDD"],
  "GND_NETS": ["VSS"],
  "FP_SIZING": "absolute",
  "DIE_AREA": [0, 0, 1600, 1600],
  "CORE_AREA": [365, 365, 1235, 1235],
  "PL_TARGET_DENSITY_PCT": 10,
  "GRT_ALLOW_CONGESTION": true,
  "PAD_SOUTH": ["clk_pad", "rst_n_pad", "..."],
  "PAD_EAST": ["..."],
  "PAD_NORTH": ["..."],
  "PAD_WEST": ["..."],
  "PDN_CORE_RING": true,
  "PDN_CORE_RING_VWIDTH": 15,
  "PDN_CORE_RING_HWIDTH": 15,
  "PDN_CORE_RING_VSPACING": 5,
  "PDN_CORE_RING_HSPACING": 5,
  "PDN_CORE_RING_CONNECT_TO_PADS": true,
  "PDN_CFG": "dir::pdn_cfg.tcl",
  "PNR_SDC_FILE": "dir::chip_top.sdc",
  "SIGNOFF_SDC_FILE": "dir::chip_top.sdc"
}
```

## Key parameters reference

### Floorplanning

| Parameter | Typical value | Description |
|-----------|--------------|-------------|
| FP_SIZING | "absolute" | Use explicit die dimensions |
| DIE_AREA | "0 0 500 500" | Die dimensions in um (x1 y1 x2 y2) |
| CORE_AREA | "50 50 450 450" | Core area inside padring (full-chip only) |
| FP_CORE_UTIL | 30-45 | Core utilization percentage |
| PL_TARGET_DENSITY_PCT | 40-75 | Placement density target |
| CORE_MARGIN | 17.5 | Margin for core ring fit (ORFS) |

### Timing

| Parameter | Typical value | Description |
|-----------|--------------|-------------|
| CLOCK_PERIOD | 18-30 | Clock period in ns |
| CLOCK_PORT | "clk" | External clock port name |
| CLOCK_NET | "clk" | Internal clock net (may differ with IO pads) |
| PL_RESIZER_SETUP_SLACK_MARGIN | 0.2-0.4 | Setup margin for placement resizer |
| PL_RESIZER_HOLD_SLACK_MARGIN | 0.05-0.4 | Hold margin for placement resizer |
| GRT_RESIZER_SETUP_SLACK_MARGIN | 0.2 | Setup margin for routing resizer |
| GRT_RESIZER_HOLD_SLACK_MARGIN | 0.01-0.2 | Hold margin for routing resizer |
| MAX_TRANSITION_CONSTRAINT | 1.0 | Max transition time in ns |
| MAX_FANOUT_CONSTRAINT | 16 | Global max fanout |
| SYNTH_MAX_FANOUT | 4-6 | Per-cell fanout limit in synthesis |

### Antenna protection

| Parameter | Typical value | Description |
|-----------|--------------|-------------|
| DIODE_CELL | "sg13g2_antennanp/A" | IHP antenna diode cell |
| RUN_HEURISTIC_DIODE_INSERTION | 1 | Enable heuristic diode insertion |
| HEURISTIC_ANTENNA_THRESHOLD | 110 | Antenna ratio threshold |
| RUN_ANTENNA_REPAIR | 1 | Enable antenna repair in routing |
| DIODE_ON_PORTS | "in" | Insert diodes on input ports |

### Synthesis

| Parameter | Typical value | Description |
|-----------|--------------|-------------|
| SYNTH_BUFFERING | 0 or 1 | Enable auto-buffering (disable for small designs) |
| QUIT_ON_SYNTH_CHECKS | true/false | Stop on synthesis warnings |
| VERILOG_DEFINES | ["FUNCTIONAL"] | Verilog defines for conditional compilation |

### Disabling steps (debugging / speed)

In `meta.substituting_steps`, set to null to disable:

```json
"meta": {
  "substituting_steps": {
    "Checker.IllegalOverlap": null,
    "KLayout.DRC": null,
    "Magic.DRC": null,
    "KLayout.Antenna": null,
    "OpenROAD.IRDropReport": null,
    "Netgen.LVS": null
  }
}
```

## Flow steps (default order)

```
Yosys.Synthesis
OpenROAD.CheckSDCFiles
OpenROAD.Floorplan
OpenROAD.GeneratePDN
OpenROAD.IOPlacement
OpenROAD.GlobalPlacement
OpenROAD.RepairDesign
OpenROAD.DetailedPlacement
OpenROAD.GlobalRouting
OpenROAD.DetailedRouting
OpenROAD.FillInsertion
Magic.StreamOut
Magic.DRC
Checker.MagicDRC
Magic.SpiceExtraction
Netgen.LVS
Checker.LVS
```

## Cross-PDK configuration pattern

LibreLane configs support PDK-conditional sections. Useful for designs that target multiple PDKs:

```json
{
  "DESIGN_NAME": "my_design",
  "CLOCK_PERIOD": 25,
  "pdk::ihp-sg13g2*": {
    "CLOCK_PERIOD": 25,
    "FP_CORE_UTIL": 35,
    "DIODE_CELL": "sg13g2_antennanp/A"
  },
  "pdk::sky130*": {
    "CLOCK_PERIOD": 15,
    "FP_CORE_UTIL": 45
  }
}
```

## Reference template

The canonical full-chip LibreLane reference for IHP SG13G2:
https://github.com/IHP-GmbH/ihp-sg13g2-librelane-template

This template provides the Chip flow with padring, bond pads, SRAM macros, custom PDN, and cocotb testbench. It is the starting point for full-chip designs and is being adapted for the SG13CMOS5L PDK as well.

Production testcases with multiple complexity levels (inverter through picorv32a CPU):
https://github.com/IHP-GmbH/ihp-librelane-testcases (or similar testcase repos)

## IHP-specific considerations

- **No tapcells/endcaps**: The IHP standard cell library lacks dedicated tap cells. LibreLane handles this via `cut_rows` in the tapcell step. Well-tie connectivity should be verified manually.
- **Bond pad not in PDK**: Bond pad cells must be supplied as EXTRA_GDS/EXTRA_LEFS from a local ip/ directory.
- **Magic overlap warnings**: `Checker.IllegalOverlap` should be nullified -- Magic reports false positives for IHP.
- **Escaped backslashes**: Array instance names in pad lists need double-escaped backslashes: `"bidirs\\[0\\].bidir_pad"`.
- **PDK version**: Use the `dev` branch of IHP-Open-PDK for latest support.
- **Standard cell library**: `sg13g2_stdcell` -- single library, no multi-Vt variants.
- **Cell height matching**: `MATCH_CELL_FOOTPRINT = 1` is set at platform level to prevent height mismatches during gate sizing.
- **Tool versions** (pinned in testcases): LibreLane 3.0.0.dev43, OpenROAD 2025-06-12, Yosys 0.54, Magic 8.3.528.

## Die area estimation guidelines

| Design complexity | Gate count | Suggested DIE_AREA | FP_CORE_UTIL |
|-------------------|-----------|-------------------|--------------|
| Trivial (inverter) | < 100 | 50 x 50 um | 75% |
| Small (timer) | 1K-5K | 200 x 200 um | 35-45% |
| Medium (encoder) | 5K-20K | 500 x 700 um | 35-40% |
| Large (CPU core) | 20K-100K | 1000 x 1000 um | 30-35% |
| Full chip with pads | Any | 1600 x 1600 um | 10-25% |
