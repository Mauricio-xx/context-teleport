---
name: characterize-device
description: Generate and use gm/ID lookup tables for IHP SG13G2 transistor sizing using pygmid or gmid tools
---

# Characterize Device via gm/ID (IHP SG13G2)

## When to use

When designing analog circuits on IHP SG13G2 and you need to size transistors systematically. The gm/ID methodology replaces square-law hand calculations with SPICE-generated lookup tables that capture real transistor behavior across all operating regions.

## What gm/ID gives you

| Parameter | Unit | What it tells you |
|-----------|------|-------------------|
| gm/ID | V^-1 | Transconductance efficiency. Selects operating region |
| fT | Hz | Transit frequency. Speed/bandwidth limit |
| Vdsat | V | Saturation voltage. Headroom budget |
| ID/W | A/um | Current density. Used to compute W |
| gm/gds | - | Intrinsic voltage gain |

Operating region by gm/ID value:
- **5-8 V^-1**: Strong inversion (fast, higher power, lower gm per current)
- **10-15 V^-1**: Moderate inversion (good tradeoff for most designs)
- **18-25 V^-1**: Weak inversion (lowest power, slow, highest gm efficiency)

## Available devices in IHP SG13G2

| Device | Type | VDD | Min L | Vth (typ) |
|--------|------|-----|-------|-----------|
| sg13_lv_nmos | LV NMOS | 1.5V | 0.13 um | ~0.5V |
| sg13_lv_pmos | LV PMOS | 1.5V | 0.13 um | ~-0.47V |
| sg13_hv_nmos | HV NMOS | 3.3V | 0.45 um | ~0.7V |
| sg13_hv_pmos | HV PMOS | 3.3V | 0.45 um | ~-0.65V |

MOSFET compact model: PSP 103.6 (compiled via OpenVAF to `psp103_nqs.osdi`).

Parameters in xschem: W (width), L (length), ng (number of gate fingers), m (multiplier).

## Generating lookup tables

### Prerequisites

1. PDK installed with OpenVAF-compiled OSDI model:
   ```bash
   cd $PDK_ROOT/ihp-sg13g2/libs.tech/verilog-a
   source openvaf-compile-va.sh
   # Produces psp103_nqs.osdi in libs.tech/ngspice/osdi/
   ```
2. `.spiceinit` symlink: `ln -s $PDK_ROOT/ihp-sg13g2/ngspice/.spiceinit ~/.spiceinit`
3. ngspice installed (with OSDI support)

### Method 1: Using gmid (medwatt/gmid)

```python
from mosplot import LookupTableGenerator

gen = LookupTableGenerator(
    simulator="ngspice",
    model_paths=["$PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/models"],
    model_names=["sg13_lv_nmos"],
    temperature=27,
)

gen.set_sweep(
    vgs={"start": 0, "stop": 1.5, "step": 0.01},
    vds={"start": 0, "stop": 1.5, "step": 0.05},
    vbs={"start": -1.5, "stop": 0, "step": 0.3},
    lengths=[0.13e-6, 0.2e-6, 0.5e-6, 1e-6, 2e-6, 5e-6],
    width=10e-6,
    nfing=1,
)

gen.build("sg13_lv_nmos.npz")
```

### Method 2: Using xschem testbenches (JKU course)

Pre-built testbenches are available in `iic-jku/analog-circuit-design`:
- `techsweep_sg13g2_lv_nmos.sch`
- `techsweep_sg13g2_lv_pmos.sch`

These run parametric DC sweeps across VGS, VDS, VSB, and L, extracting all operating-point parameters.

### Method 3: Manual ngspice sweep

```spice
* Techsweep for sg13_lv_nmos
.lib $PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/models/cornerMOSlv.lib mos_tt
.include $PDK_ROOT/ihp-sg13g2/libs.tech/ngspice/models/diodes.lib

M1 d g 0 0 sg13_lv_nmos W=10u L=0.13u

Vgs g 0 0
Vds d 0 0.6

.control
let L_vals = ( 0.13u 0.2u 0.5u 1u 2u 5u )
* Sweep VGS for each L, extract gm, gds, id, cgg, vth, vdsat
foreach L_val $&L_vals
  alter @M1[L] = $L_val
  dc Vgs 0 1.5 0.01
  * Extract: @M1[gm], @M1[gds], @M1[id], @M1[cgg], @M1[vth], @M1[vdsat]
end
.endc
```

## Using LUTs for transistor sizing

### Design flow (5 steps)

**Step 1: Derive circuit requirements.**
From the circuit topology (e.g., 5T OTA), write gm requirements:
- Gain: Av = gm1 * (1/gds2 || 1/gds4)
- Bandwidth: GBW = gm1 / (2*pi*CL)
- Slew rate: SR = I_tail / CL

**Step 2: Choose gm/ID operating point.**
This is the primary design decision:
- Low power: gm/ID = 18-22 (weak inversion)
- Balanced: gm/ID = 12-15 (moderate inversion)
- High speed: gm/ID = 6-10 (strong inversion)

**Step 3: Look up fT and ID/W at chosen gm/ID and L.**
```python
from mosplot.plot import load_lookup_table, Mosfet

lut = load_lookup_table("sg13_lv_nmos.npz")
nmos = Mosfet(lookup_table=lut, mos="sg13_lv_nmos",
              vbs=0.0, vds=0.6, vgs=(0.01, 1.50))

# Plot gm/ID vs ID/W for different L values
nmos.plot_by_expression(
    x_expression=nmos.gmid_expression,
    y_expression=nmos.current_density_expression,
    filtered_values=nmos.length[::2],
)
```

**Step 4: Size transistors.**
- From circuit equations: required gm for each transistor
- ID = gm / (gm/ID)
- W = ID / (ID/W from LUT at chosen L)
- Round to nearest finger width

**Step 5: Verify in SPICE.**
Enter sized schematic in xschem, run DC op, AC, and transient. Results should closely match LUT predictions.

## Process corners

Corner model libraries:
- `cornerMOSlv.lib` -- Low-voltage MOSFET corners
- `cornerMOShv.lib` -- High-voltage MOSFET corners
- `cornerHBT.lib` -- Bipolar transistor corners

| Corner | Selection | Use |
|--------|----------|-----|
| Typical | `mos_tt` | Nominal design point |
| Fast-Fast | `mos_ff` | Best speed, hold analysis |
| Slow-Slow | `mos_ss` | Worst speed, setup analysis |
| Slow-Fast | `mos_sf` | NMOS slow, PMOS fast |
| Fast-Slow | `mos_fs` | NMOS fast, PMOS slow |

Temperature range: -40C to 125C (industrial).

Mismatch models:
```spice
.include sg13g2_moslv_mismatch.lib
.param mc_ok=1
```

## Passive components for reference

| Component | Type | Sheet R / Cap | TC (ppm/K) |
|-----------|------|--------------|-----------|
| rsil | Silicided poly | 7 Ohm/sq | 3100 |
| rppd | Standard poly | 260 Ohm/sq | 170 |
| rhigh | High-value poly | 1360 Ohm/sq | -2300 |
| cap_cmim | MIM cap | 1.5 fF/um^2 | - |

## Bipolar transistors (SiGe HBTs)

Available for bandgap references, LNAs, VCOs:

| Device | Type | fT | fmax |
|--------|------|-----|------|
| npn13g2 | Standard NPN | 350 GHz | 450 GHz |
| npn13g2l | Long-emitter | Variable | Variable |
| npn13g2v | High-power | Variable | Variable |
| pnpMPA | PNP (bandgap) | Low | Low |

Model: VBIC (native ngspice, no OSDI needed).

## Tools and references

- **pygmid** (PyPI): Python port of Murmann's gm/ID starter kit. Supports .mat and .pkl LUTs.
- **gmid** (medwatt/gmid): Full pipeline -- LUT generation, plotting, optimization. NPZ output. Parallel builds.
- **pyMOSChar**: Another Python port supporting ngspice and spectre.
- **ihp-gmid-kit**: IHP-specific gm/ID toolkit with Jupyter tutorials.
- **iic-jku/analog-circuit-design**: JKU course with techsweep notebooks for SG13G2.
- **IHP AnalogAcademy**: 4-module course covering gm/ID, bandgap, PA, SAR ADC on SG13G2.
