---
name: xschem-simulate
description: Set up and run xschem-to-ngspice simulation workflows for IHP SG13G2 analog designs
---

# Xschem to Simulation (IHP SG13G2)

## When to use

When creating or modifying analog schematics in xschem for IHP SG13G2 and running SPICE simulations with ngspice. Covers environment setup, schematic capture, simulation types, and result analysis.

## Environment setup

### Prerequisites

1. **PDK cloned**:
   ```bash
   git clone --branch dev --recurse-submodules https://github.com/IHP-GmbH/IHP-Open-PDK.git
   ```

2. **Environment variables** (add to `.bashrc`):
   ```bash
   export PDK_ROOT=$HOME/<path>/IHP-Open-PDK
   export PDK=ihp-sg13g2
   export KLAYOUT_PATH="$HOME/.klayout:$PDK_ROOT/$PDK/libs.tech/klayout"
   ```

3. **Compile PSP model** (mandatory for MOSFET simulation):
   ```bash
   cd $PDK_ROOT/$PDK/libs.tech/verilog-a
   source openvaf-compile-va.sh
   # Produces psp103_nqs.osdi in libs.tech/ngspice/osdi/
   ```

4. **Create .spiceinit symlink**:
   ```bash
   ln -s $PDK_ROOT/$PDK/ngspice/.spiceinit ~/.spiceinit
   ```

5. **Docker alternative**: `iic-jku/IIC-OSIC-TOOLS` has everything pre-configured.

### Xschem configuration

Create `xschemrc` in your working directory:
```tcl
source $env(PDK_ROOT)/$env(PDK)/libs.tech/xschem/xschemrc
append XSCHEM_LIBRARY_PATH :$env(PWD)
```

### PDK symbol library

Symbols: `$PDK_ROOT/$PDK/libs.tech/xschem/sg13g2_pr/`
Test schematics: `$PDK_ROOT/$PDK/libs.tech/xschem/sg13g2_tests/`
Top-level testcase: `IHP_testcases.sch`

## Schematic capture to simulation flow

1. **Draw schematic** in xschem: Place PDK device symbols, wire connections, add voltage sources and ground
2. **Add model includes** via `code_shown` attribute:
   ```spice
   .lib cornerMOSlv.lib mos_tt
   .include $PDK_ROOT/$PDK/libs.tech/ngspice/models/diodes.lib
   ```
3. **Add simulation commands** via `code` attribute (`.dc`, `.ac`, `.tran`, etc.)
4. **Generate netlist**: Click "Netlist" or press `n`. Output: `simulations/<name>.spice`
5. **Run simulation**: Click "Simulate" (launches ngspice) or: `ngspice simulations/<name>.spice`
6. **View waveforms**: Click "Waves" or use ngspice `plot` commands. In xschem, select nets and press `Shift+J`.

## Simulation types

All examples below use the actual IHP SG13G2 syntax from `$PDK_ROOT/ihp-sg13g2/libs.tech/xschem/sg13g2_tests/`.

### DC Operating Point and IV Curves

From `dc_lv_nmos.sch` -- characterize NMOS I/V family:

```spice
.param temp=27
.control
save all
op
write dc_lv_nmos.raw
set appendwrite
dc Vds 0 1.2 0.01 Vgs 0.3 1.0 0.1
write dc_lv_nmos.raw
.endc
```

Device instantiation in netlist (hierarchical, `spiceprefix=X`):
```spice
X M1 d g 0 0 sg13_lv_nmos W=1.0u L=0.45u ng=1 m=1
```

### AC Analysis (frequency response, impedance extraction)

From `ac_mim_cap.sch` -- extract MIM capacitance:

```spice
.control
save all
ac dec 1000 1e6 1e9
let mag=abs(out)
meas ac freq_at when mag = 0.707
let C = 1/(2*PI*freq_at*1e+5)
print C
write ac_mim_cap.raw
.endc
```

For amplifier gain-bandwidth:

```spice
.control
set num_threads=1
save all
op
write inv_mc_tb.raw
set appendwrite
ac dec 1001 1 100G
write inv_mc_tb.raw
let gain_lin = abs(inv_out)
let gain_dB = vdb(inv_out)
meas ac gain_passband_dB max gain_dB
let gain_fc_dB = gain_passband_dB-3
meas ac fc_l when gain_dB = gain_fc_dB
meas ac fc_u when gain_dB = gain_fc_dB cross=last
let GBW = gain_lin[0] * (fc_u-fc_l)
print gain_passband_dB
.endc
```

### Transient Analysis

From `tran_logic_not.sch` -- inverter delay measurement:

```spice
.param temp=27
.control
save all
tran 50p 20n
meas tran tdelay TRIG v(in) VAL=0.9 FALL=1 TARG v(out) VAL=0.9 RISE=1
write tran_logic_not.raw
.endc
```

Pulse source syntax (in xschem `value` attribute):
```spice
dc 0 ac 0 pulse(0, 1.8, 0, 100p, 100p, 2n, 4n)
```

### Temperature Sweep

```spice
.control
save all
dc temp -40 125 1
write mos_temp.raw
wrdata mos_temp.csv I(Vm1) I(Vm2) I(Vm3) I(Vm4)
.endc
```

### Corner Analysis (PVT)

Model include block (in xschem `code_shown`):
```spice
.lib cornerMOSlv.lib mos_tt
.lib $::MODELS_NGSPICE/cornerCAP.lib cap_typ
.include $::MODELS_NGSPICE/diodes.lib
```

Run multiple corners by changing the library selection:

| Corner combo | MOSFET lib | CAP lib | RES lib | Temp |
|-------------|-----------|---------|---------|------|
| Typical | mos_tt | cap_typ | res_typ | 27C |
| Slow | mos_ss | cap_wcs | res_wcs | 125C |
| Fast | mos_ff | cap_bcs | res_bcs | -40C |

Automate with a script that launches ngspice multiple times, each with a different `.lib` selection and temperature.

### Monte Carlo / Mismatch

From `mc_lv_nmos_cs_loop.sch` -- 1000-iteration MC loop:

```spice
.param mm_ok=1
.param mc_ok=1
.control
let mc_runs = 1000
let run = 0
set curplot=new
set scratch=$curplot
setplot $scratch
let vg=unitvec(mc_runs)

dowhile run < mc_runs
  op
  set run=$&run
  set dt=$curplot
  setplot $scratch
  let out{$run}={$dt}.Vgs
  let Vg[run]={$dt}.Vgs
  setplot $dt
  reset
  let run=run+1
end

wrdata sg13_lv_nmos_cs.csv {$scratch}.vg
write sg13_lv_nmos_cs.raw
.endc
```

Key: `reset` between iterations forces re-evaluation of AGAUSS functions. Post-process CSV with Python scripts (e.g., `MC_mos.py` in the PDK) to extract mean/std and histograms.

## Output patterns

```spice
save all                          ; Save all node voltages and branch currents
write filename.raw                ; Binary output (ngspice native)
set appendwrite                   ; Append subsequent writes to same .raw file
wrdata filename.csv v(out) i(Vm)  ; ASCII CSV for post-processing
print expr                        ; Print to terminal
```

## Testbench structure pattern

A typical xschem testbench for IHP SG13G2:

```
+------------------------------------------+
|  DUT (subcircuit or direct placement)     |
|  - PDK device symbols                     |
|  - Internal wiring                        |
+------------------------------------------+
|  Stimulus                                 |
|  - VDD supply (1.2V or 3.3V)             |
|  - Input voltage sources (DC, pulse, sin) |
|  - Load capacitors                        |
+------------------------------------------+
|  code_shown block                         |
|  - .lib model includes                    |
|  - .temp temperature setting              |
|  - .param definitions                     |
+------------------------------------------+
|  code block                               |
|  - .dc / .ac / .tran commands             |
|  - .measure statements                    |
|  - .control block for post-processing     |
+------------------------------------------+
|  Net labels for probing                   |
|  - vout, vin, vbias, etc.                 |
+------------------------------------------+
```

## Available devices

### MOSFETs

| Device | Type | VDD | Lmin | Vth (typ) |
|--------|------|-----|------|-----------|
| sg13_lv_nmos | LV NMOS | 1.5V | 0.13 um | ~0.5V |
| sg13_lv_pmos | LV PMOS | 1.5V | 0.13 um | ~-0.47V |
| sg13_hv_nmos | HV NMOS | 3.3V | 0.45 um | ~0.7V |
| sg13_hv_pmos | HV PMOS | 3.3V | 0.45 um | ~-0.65V |

Model: PSP 103.6 (via OSDI/OpenVAF). Parameters: W, L, ng (fingers), m (multiplier).

### BJTs (SiGe HBTs)

| Device | fT | fmax | Use |
|--------|-----|------|-----|
| npn13g2 | 350 GHz | 450 GHz | High-speed amplifiers |
| npn13g2l | Variable | Variable | Longer emitter |
| npn13g2v | Variable | Variable | Higher power |
| pnpMPA | Low | Low | Bandgap references |

Model: VBIC (native ngspice). Parameters: Nx (devices), El (emitter length for l/v variants).

### Passives

| Device | Type | Value | Notes |
|--------|------|-------|-------|
| rsil | Silicided poly | 7 Ohm/sq | Low-value, high TC |
| rppd | Standard poly | 260 Ohm/sq | Medium-value, low TC |
| rhigh | High-R poly | 1360 Ohm/sq | High-value, negative TC |
| cap_cmim | MIM capacitor | 1.5 fF/um^2 | >15V breakdown |
| dantenna | Antenna diode | - | N-type |
| dpantenna | Antenna diode | - | P-type |

## Process corners

| Corner | Selection | Temperature | Use |
|--------|----------|-------------|-----|
| mos_tt | Typical | 27C | Nominal design |
| mos_ff | Fast-Fast | -40C | Hold timing, max speed |
| mos_ss | Slow-Slow | 125C | Setup timing, min speed |
| mos_sf | Slow N / Fast P | Varies | Differential pair skew |
| mos_fs | Fast N / Slow P | Varies | Differential pair skew |
| hbt_typ | Typical HBT | 27C | Bipolar nominal |

Industrial temperature range: -40C to 125C.

## Common issues

- **"No module named imp"**: Python 3.12 compatibility issue with KLayout. Use Python 3.11.
- **Missing OSDI file**: If MOSFETs don't simulate, verify `psp103_nqs.osdi` exists in `libs.tech/ngspice/osdi/`.
- **Missing .spiceinit**: Creates error about missing model files. Ensure symlink exists in `$HOME`.
- **Slow Monte Carlo**: ngspice re-parses on each iteration. For >100 runs, consider a batch script approach.
- **Convergence issues**: For large circuits, add `.option reltol=1e-3 abstol=1e-12 vntol=1e-6` to relax tolerances.
