---
name: configure-pdn
description: Configure power delivery network for IHP SG13G2 designs in LibreLane and ORFS flows
---

# Configure PDN (IHP SG13G2)

## When to use

When setting up or debugging the power delivery network for a digital design targeting IHP SG13G2. Covers both LibreLane and ORFS flows.

## IHP SG13G2 metal stack for PDN

| Layer | Type | Min width | Min space | PDN use |
|-------|------|-----------|-----------|---------|
| Metal1 | Thin Al | 0.16 um | 0.18 um | Standard cell rails (followpins) |
| Metal2-5 | Thin Al | 0.20 um | 0.21 um | Signal routing (not PDN typically) |
| TopMetal1 | Thick Al (~2 um) | 1.64 um | 1.64 um | Vertical power straps, core ring |
| TopMetal2 | Thick Al (~3 um) | 2.0 um | 2.0 um | Horizontal power straps, core ring |

Key constraints:
- **Max unslotted metal width**: 30 um. Keep ring widths under 15 um per strap.
- **TopMetal1/TopMetal2** are the primary PDN layers due to low resistance.
- **Metal1** is used for standard cell rail connections (followpins).
- **Metal2-5** are for signal routing -- avoid using them for PDN unless necessary.

## ORFS default PDN (pdn.tcl)

The IHP platform in ORFS provides this default PDN configuration:

```tcl
# Global connections
add_global_connection -net {VDD} -pin_pattern {^VDD$} -power
add_global_connection -net {VDD} -pin_pattern {^VDDPE$}
add_global_connection -net {VDD} -pin_pattern {^VDDCE$}
add_global_connection -net {VSS} -pin_pattern {^VSS$} -ground
add_global_connection -net {VSS} -pin_pattern {^VSSE$}
global_connect

# Voltage domain
set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}

# Grid with pins on thick metals
define_pdn_grid -name {grid} -voltage_domains {CORE} -pins {TopMetal1 TopMetal2}

# Core ring on thick metals
add_pdn_ring -grid {grid} -layers {TopMetal1 TopMetal2} \
  -widths {5.0} -spacings {2.0} -core_offsets {4.5} -connect_to_pads

# Standard cell rails on Metal1
add_pdn_stripe -grid {grid} -layer {Metal1} -width {0.44} -pitch {7.56} \
  -offset {0} -followpins -extend_to_core_ring

# Vertical straps on TopMetal1
add_pdn_stripe -grid {grid} -layer {TopMetal1} -width {2.200} -pitch {75.6} \
  -offset {13.600} -extend_to_core_ring

# Horizontal straps on TopMetal2
add_pdn_stripe -grid {grid} -layer {TopMetal2} -width {2.200} -pitch {75.6} \
  -offset {13.600} -extend_to_core_ring

# Via connections
add_pdn_connect -grid {grid} -layers {Metal1 TopMetal1}
add_pdn_connect -grid {grid} -layers {TopMetal1 TopMetal2}
```

### Parameter rationale

| Parameter | Value | Why |
|-----------|-------|-----|
| Ring layers | TopMetal1 + TopMetal2 | Thick metals for low resistance |
| Ring width | 5.0 um | Balance between IR drop and area (max 15 um before slotting needed) |
| Ring spacing | 2.0 um | Minimum VDD-VSS gap for thick metals |
| Ring offset | 4.5 um | Clearance from core boundary |
| Metal1 followpins | w=0.44, pitch=7.56 | Matches standard cell rail pitch |
| TopMetal1 straps | w=2.2, pitch=75.6 | Vertical power distribution |
| TopMetal2 straps | w=2.2, pitch=75.6 | Horizontal power distribution |

## LibreLane PDN configuration

### In config.json (basic parameters)

```json
{
  "pdk::ihp-sg13g2*": {
    "FP_PDN_VPITCH": 25,
    "FP_PDN_HPITCH": 25,
    "FP_PDN_VOFFSET": 5,
    "FP_PDN_HOFFSET": 5,
    "VDD_NETS": ["VDD"],
    "GND_NETS": ["VSS"]
  }
}
```

### Custom PDN Tcl script (for full-chip or macros)

Reference from the LibreLane template (`pdn_cfg.tcl`):

```tcl
add_global_connection -net {VDD} -pin_pattern {^VDD$} -power
add_global_connection -net {VSS} -pin_pattern {^VSS$} -ground
global_connect

set_voltage_domain -name {CORE} -power {VDD} -ground {VSS}
define_pdn_grid -name {grid} -voltage_domains {CORE} -pins {TopMetal1 TopMetal2}

add_pdn_ring -grid {grid} -layers {TopMetal1 TopMetal2} \
  -widths {15.0} -spacings {5.0} -core_offsets {4.5} -connect_to_pads

add_pdn_stripe -grid {grid} -layer {Metal1} -width {0.44} -pitch {7.56} \
  -offset {0} -followpins -extend_to_core_ring

add_pdn_stripe -grid {grid} -layer {TopMetal1} -width {2.200} -pitch {75.6} \
  -offset {13.600} -extend_to_core_ring

add_pdn_stripe -grid {grid} -layer {TopMetal2} -width {2.200} -pitch {75.6} \
  -offset {13.600} -extend_to_core_ring

add_pdn_connect -grid {grid} -layers {Metal1 TopMetal1}
add_pdn_connect -grid {grid} -layers {TopMetal1 TopMetal2}
```

Enable in config.json:
```json
"PDN_CFG": "dir::pdn_cfg.tcl"
```

## Full chip with IO pads

When using IO pads (LibreLane Chip flow), additional considerations:

```json
{
  "PDN_CORE_RING": true,
  "PDN_CORE_RING_VWIDTH": 15,
  "PDN_CORE_RING_HWIDTH": 15,
  "PDN_CORE_RING_VSPACING": 5,
  "PDN_CORE_RING_HSPACING": 5,
  "PDN_CORE_RING_CONNECT_TO_PADS": true,
  "PDN_ENABLE_PINS": false,
  "VDD_NETS": ["VDD"],
  "GND_NETS": ["VSS"]
}
```

For designs with separate IO power domain:
```tcl
add_global_connection -net {IOVDD} -pin_pattern {^iovdd$} -power
add_global_connection -net {IOVSS} -pin_pattern {^iovss$} -ground
```

## SRAM macro PDN connections

When integrating SRAM macros, explicitly connect their power pins:

```json
"PDN_MACRO_CONNECTIONS": [
  "i_chip_core.sram_0 VDD VSS VDDARRAY! VSS!",
  "i_chip_core.sram_0 VDD VSS VDD! VSS!"
]
```

## Common PDN issues and fixes

### PSM-0042: "Unable to connect macro/pad to power grid"

**Root cause**: Misaligned power pins in IO cell LEFs where TopMetal2 OBS layers cover TopMetal1 VDD/VSS pins.

**Fix**: Update to latest PDK LEFs. See ORFS issue #1667.

### Global routing blocked by PDN on horizontal pads

**Root cause**: TopMetal1/TopMetal2 core ring blocks signal routing to horizontally-placed IO pads.

**Fix**: Use Metal5 + TopMetal1 for PDN instead of TopMetal1 + TopMetal2. This avoids blocking IO pad pins. Example from ORFS i2c-gpio-expander design.

### IR drop too high

**Symptoms**: `check_power_grid` reports excessive voltage drop. Design fails at target frequency.

**Fixes**:
- Increase strap width (but stay under 30 um to avoid slotting DRC)
- Decrease strap pitch (more straps = lower resistance)
- Add straps on intermediate metal layers (Metal3 or Metal4)
- Increase core ring width

### Missing IO pad power connections

**Symptom**: `check_power_grid` passes but IO pads don't work.

**Root cause**: IO nets appear connected through the ring but actual pad power cells are missing.

**Fix**: Always verify IO pad power explicitly. Ensure IOPadIOVdd and IOPadIOVss cells are placed.

## PDN sizing guidelines for IHP

| Die area | Strap pitch | Strap width | Ring width | Notes |
|----------|-------------|-------------|------------|-------|
| < 200x200 um | 25-50 um | 2.0 um | 5.0 um | Minimal design |
| 200-1000 um | 50-75 um | 2.2 um | 5.0-10.0 um | Standard |
| > 1000 um | 75-100 um | 2.2-4.0 um | 10.0-15.0 um | Large design |
| Full chip with pads | 75 um | 2.2 um | 15.0 um | Connect to pads |

CORE_MARGIN should be at least `ring_width + ring_spacing + ring_offset` to ensure the ring fits inside the die.
