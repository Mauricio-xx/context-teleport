---
name: port-design
description: Guide for porting analog and digital designs between PDKs, with focus on Sky130-to-IHP SG13G2 adaptation
---

# Port Design Between PDKs

## When to use

When adapting an existing design from one PDK (typically Sky130) to IHP SG13G2, or when evaluating what changes are required for a PDK migration. Covers both analog (schematic/simulation) and digital (RTL-to-GDS) porting.

## Key differences: Sky130 vs IHP SG13G2

### Voltage domains

| Parameter | Sky130 | IHP SG13G2 |
|-----------|--------|------------|
| Core VDD | 1.8V | 1.2V (digital) / 1.5V (analog LV) |
| IO VDD | 3.3V / 5.0V | 3.3V |
| LV NMOS Vth | ~0.7V | ~0.5V |
| LV PMOS Vth | ~-0.7V | ~-0.47V |
| HV NMOS Vth | ~0.65V (3.3V) | ~0.7V |
| HV PMOS Vth | ~-0.75V | ~-0.65V |

Impact: All biasing must be recalculated. Headroom allocation changes significantly. Cascode stages designed for 1.8V may not have enough headroom at 1.2-1.5V.

### Device models

| Aspect | Sky130 | IHP SG13G2 |
|--------|--------|------------|
| MOSFET model | BSIM3v3 / BSIM4 | PSP 103.6 (via OSDI) |
| Model loading | Native ngspice | Requires psp103_nqs.osdi |
| HBT devices | None | SiGe npn-HBT (350 GHz fT) |
| Device names | sky130_fd_pr__nfet_01v8 | sg13_lv_nmos |
| Min L (LV) | 0.15 um | 0.13 um |
| Min L (HV) | 0.5 um | 0.45 um |

### Metal stack

| Aspect | Sky130 | IHP SG13G2 |
|--------|--------|------------|
| Metal type | Copper (5 layers + LI) | Aluminum (7 layers) |
| Local interconnect | li1 | None (use Metal1) |
| Thin metals | met1-met4 | Metal1-Metal5 |
| Thick metals | met5 | TopMetal1 (2um), TopMetal2 (3um) |
| Routing layers | 5 + LI | 7 |
| MIM cap | Between met3/met4 | Dedicated layer between Metal5/TopMetal1 |

### Standard cells

| Aspect | Sky130 | IHP SG13G2 |
|--------|--------|------------|
| Libraries | Multiple (hd, hs, ms, ls, hdll) | Single (sg13g2_stdcell) |
| Multi-Vt | Yes (hvl, svt, lvt) | No |
| Tap cells | Yes (sky130_fd_sc_hd__tapvpwrvgnd) | No (manual well ties) |

### Passives

| Component | Sky130 | IHP SG13G2 |
|-----------|--------|------------|
| Poly R (precision) | ~48.2 Ohm/sq (p_res_xhigh) | rsil (7), rppd (260), rhigh (1360 Ohm/sq) |
| MIM cap density | ~2 fF/um^2 | 1.5 fF/um^2 |
| Inductor support | Limited | Better (thick TopMetal1/2) |

## What must be redone when porting

### Analog designs (full redo)

1. **Regenerate gm/ID lookup tables** for IHP process. Old Sky130 LUTs are useless -- the entire point is process-specific data.
2. **Recalculate all bias points** -- Different Vth, different VDD, different current densities.
3. **Resize all transistors** using new LUTs -- W/L ratios will differ.
4. **Rewrite model includes**:
   ```spice
   * Sky130:
   .lib sky130_fd_pr/models/sky130.lib.spice tt

   * IHP SG13G2:
   .lib cornerMOSlv.lib mos_tt
   .include $PDK_ROOT/$PDK/libs.tech/ngspice/models/diodes.lib
   ```
5. **Map device names**:
   ```
   sky130_fd_pr__nfet_01v8  ->  sg13_lv_nmos
   sky130_fd_pr__pfet_01v8  ->  sg13_lv_pmos
   sky130_fd_pr__nfet_g5v0d10v5  ->  sg13_hv_nmos
   sky130_fd_pr__pfet_g5v0d10v5  ->  sg13_hv_pmos
   ```
6. **Update testbenches** -- New VDD values, new model includes, new device names.
7. **Re-verify across new corners** -- Different corner models mean different worst-case conditions.
8. **Leverage new devices** -- IHP offers SiGe HBTs (350 GHz fT) that Sky130 lacks. Bandgap references can use real HBTs instead of parasitic bipolars.

### Digital designs (largely automated)

1. **Update config** -- Change PDK target, adjust clock period and timing margins.
2. **Re-synthesize** -- Different cell library, different drive strengths, different timing.
3. **Adjust floorplan** -- Different die area requirements for the same gate count.
4. **Update PDN** -- Different metal stack, different power strap strategy.
5. **Handle missing cells**:
   - No tap cells: Verify well-tie connectivity manually
   - No multi-Vt: Cannot optimize for power via threshold voltage mixing
   - Antenna diode: Use `sg13g2_antennanp` instead of `sky130_fd_sc_hd__diode_2`
6. **Update SDC** -- Different clock period targets for 130nm vs 130nm (similar) or 180nm vs 130nm (different).
7. **Re-run DRC/LVS** -- Completely different rule decks.

### Layout (full redo for analog, automated for digital)

- **Analog layout**: Must be completely redone. Different DRC rules, metal stack, min dimensions.
- **Digital layout**: Automated by P&R tool (LibreLane/ORFS). Just update the config.
- **Layer mapping**: Sky130 `li1` has no equivalent in IHP -- routes must go to Metal1.
- **Parasitic extraction**: Completely different extraction models (Al vs Cu, different layer thicknesses).

## What can be preserved

- **Circuit topology** -- A 5-transistor OTA is still a 5-transistor OTA
- **Design methodology** -- gm/ID flow is process-independent; only LUT data changes
- **Testbench structure** -- Stimulus patterns and measurement scripts are largely reusable
- **Specification targets** -- Gain, bandwidth, noise targets remain (achievability may change)
- **RTL code** -- Verilog/SystemVerilog is technology-independent
- **Verification testbenches** -- cocotb, UVM, etc. are reusable

## Porting checklist

### Analog

- [ ] Regenerate gm/ID LUTs for all IHP device types needed
- [ ] Recalculate bias points at new VDD (1.2V core / 3.3V IO)
- [ ] Check headroom: cascode stages may not fit in 1.2V
- [ ] Resize all transistors from new LUTs
- [ ] Update all SPICE model includes to IHP format
- [ ] Map all device names (Sky130 -> IHP)
- [ ] Update VDD in testbenches
- [ ] Run DC op, AC, transient at typical corner
- [ ] Run full PVT corners (tt/ff/ss/sf/fs x -40/27/125C)
- [ ] Run Monte Carlo if design requires matching
- [ ] Consider topology changes to exploit HBTs (if applicable)

### Digital

- [ ] Create config.json for LibreLane with IHP-specific parameters
- [ ] Set conservative clock period (25 ns initial target)
- [ ] Configure antenna diode: `sg13g2_antennanp/A`
- [ ] Set core utilization (30-45% depending on complexity)
- [ ] Run synthesis and check gate count
- [ ] Run full flow: floorplan -> place -> CTS -> route -> finish
- [ ] Check timing at each stage (WNS >= 0)
- [ ] Run DRC and LVS on final GDS
- [ ] Verify well-tie connectivity (no tap cells in IHP)

## Clock period translation guide

When porting from a design that ran at frequency F on another PDK:

| Original PDK | Original freq | IHP SG13G2 target | Notes |
|-------------|--------------|-------------------|-------|
| Sky130 (130nm) | 100 MHz | 50-80 MHz | Similar node, but IHP cells are different |
| GF180MCU (180nm) | 50 MHz | 60-80 MHz | IHP 130nm is slightly faster |
| TSMC 65nm | 200 MHz | 50-80 MHz | Significant frequency reduction |
| ASAP7 (7nm) | 1 GHz | 40-60 MHz | Not comparable -- different universe |

Rule of thumb: Start at 50% of the original frequency for a different PDK, tighten after first successful closure.
