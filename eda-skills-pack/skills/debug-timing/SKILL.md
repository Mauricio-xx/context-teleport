---
name: debug-timing
description: Analyze OpenROAD/OpenSTA timing reports for IHP SG13G2 designs, identify violations, and suggest fixes
---

# Debug Timing Violations (IHP SG13G2)

## When to use

After running synthesis, placement, CTS, or routing in LibreLane or ORFS and encountering timing violations (negative WNS or TNS). This skill helps interpret timing reports, identify critical paths, and apply targeted fixes.

## Key timing metrics

- **WNS (Worst Negative Slack)**: The most violated path. Target: >= 0.
- **TNS (Total Negative Slack)**: Sum of all negative slacks. Target: 0.
- **Slack formula**: Setup: `slack = required_time - arrival_time`. Hold: `slack = arrival_time - required_time`. Positive = met, negative = violated.

## Process corners for IHP SG13G2

| Corner | Voltage | Temperature | Use case |
|--------|---------|-------------|----------|
| Slow | 1.08V | 125C | Setup analysis (worst case) |
| Typical | 1.20V | 25C | Nominal operation |
| Fast | 1.32V | -40C | Hold analysis (worst case) |

Liberty files in the PDK provide all three corners for the sg13g2_stdcell library.

## Clock period guidelines for IHP 130nm

Based on real LibreLane testcases:

| Design type | Clock period | Frequency | Notes |
|-------------|-------------|-----------|-------|
| Simple combinational | No clock | N/A | Inverter, buffer chains |
| USB interfaces | 15-16 ns | 62-67 MHz | High-speed IO |
| Encoders / audio | 17-18 ns | 55-59 MHz | Moderate logic depth |
| CPU cores (picorv32) | 24 ns | 42 MHz | Complex datapath |
| Peripherals / timers | 25 ns | 40 MHz | Conservative |
| Full chip with IO pads | 25-30 ns | 33-40 MHz | IO pad delay dominates |

**Rule of thumb**: Start at 25 ns for new designs, tighten after first successful closure. IHP 130nm is not a speed demon -- 40-60 MHz is the typical operating range.

## Reading a timing path report

```
Startpoint: reg_a (rising edge-triggered flip-flop clocked by core_clock)
Endpoint:   reg_b (rising edge-triggered flip-flop clocked by core_clock)
Path Group:  core_clock
Path Type:   max (setup)

  Delay    Time   Description
  -----    ----   -----------
  0.00     0.00   clock core_clock (rise edge)
  0.15     0.15   clock network delay (propagated)
  ...      ...    cell/net delays through combinational logic
  2.45     2.60   data arrival time

  2.80     2.80   clock core_clock (rise edge)
  0.15     2.95   clock network delay
  -0.10    2.85   clock uncertainty
  -0.05    2.80   library setup time
                  data required time
  -----    ----
                  data required time  2.80
                  data arrival time  -2.60
                  slack               0.20   (MET)
```

Key things to look for:
- **Large cell delays**: Indicates weak driving cells or high-fanout nets
- **Large net delays**: Indicates long wire routes (placement issue)
- **Clock uncertainty**: Typically 0.15-0.25 ns; if too high, clock tree needs work
- **Setup/hold time**: Library-dependent, fixed per cell type

## Setup violation fixes (data arrives too late)

Priority order:

1. **Relax clock period** -- If frequency target is flexible, increase CLOCK_PERIOD
2. **Increase slack margins** -- Give the tool more room during optimization:
   ```json
   "PL_RESIZER_SETUP_SLACK_MARGIN": 0.4,
   "GRT_RESIZER_SETUP_SLACK_MARGIN": 0.2
   ```
3. **Reduce utilization** -- Gives placer more room to shorten paths:
   ```json
   "FP_CORE_UTIL": 30,
   "PL_TARGET_DENSITY_PCT": 40
   ```
4. **Fix all paths** -- Not just the worst:
   ```
   TNS_END_PERCENT = 100
   ```
5. **Synthesis tuning**:
   - `SYNTH_MAX_FANOUT`: 4-6 (limit fanout per cell)
   - `MAX_TRANSITION_CONSTRAINT`: 1.0 (ns)
   - Do NOT use `ABC_AREA = 1` for IHP designs -- it degrades timing repair
6. **SDC refinements**:
   - Identify false paths: `set_false_path -through w1 -through w2`
   - Multi-cycle paths: `set_multicycle_path -setup 2 -from ... -to ...`
   - Set max fanout/capacitance: `set_max_fanout 8 [current_design]`

## Hold violation fixes (data arrives too early)

Hold violations only appear after CTS (ideal clock has no skew). They are more critical than setup -- a hold violation means the chip is non-functional at any frequency.

1. **Increase hold margin**:
   ```json
   "PL_RESIZER_HOLD_SLACK_MARGIN": 0.2,
   "GRT_RESIZER_HOLD_SLACK_MARGIN": 0.2
   ```
2. **Allow setup degradation to fix hold**:
   ```
   PL_RESIZER_ALLOW_SETUP_VIOS = 1
   ```
3. **Buffer insertion limit** -- Default max 20% area for hold buffers. Increase if needed:
   ```json
   "PL_RESIZER_HOLD_MAX_BUFFER_PERCENT": 60
   ```
4. **Always check timing after CTS and after detailed routing** -- post-route parasitics shift both margins.

## IHP-specific timing parameters

### RC parasitics per layer (from setRC.tcl)

| Layer | Resistance | Notes |
|-------|-----------|-------|
| Metal1 | 8.5 mohm/sq | Highest resistance -- avoid for long signal wires |
| Metal2-5 | Progressively lower | Standard routing layers |
| TopMetal1/2 | Very low | Used for power, not signal routing |

Signal wire capacitance: ~1.73e-04 pF/um. Clock wire capacitance: ~1.44e-04 pF/um.

### Default routing layers

```
MIN_ROUTING_LAYER = Metal2
MAX_ROUTING_LAYER = Metal5
```

Metal1 is reserved for standard cell internal routing. TopMetal1/2 are for power distribution.

## Timing-related config parameters

### LibreLane (config.json)

```json
{
  "CLOCK_PERIOD": 25,
  "CLOCK_PORT": "clk",
  "CLOCK_NET": "clk",
  "PL_RESIZER_SETUP_SLACK_MARGIN": 0.2,
  "PL_RESIZER_HOLD_SLACK_MARGIN": 0.2,
  "GRT_RESIZER_SETUP_SLACK_MARGIN": 0.2,
  "GRT_RESIZER_HOLD_SLACK_MARGIN": 0.2,
  "MAX_TRANSITION_CONSTRAINT": 1.0,
  "MAX_FANOUT_CONSTRAINT": 16,
  "SYNTH_MAX_FANOUT": 4
}
```

### ORFS (config.mk)

```makefile
export CLOCK_PERIOD        = 25.0
export SETUP_SLACK_MARGIN  = 0
export HOLD_SLACK_MARGIN   = 0
export TNS_END_PERCENT     = 100
export CTS_BUF_DISTANCE    = 60
export MATCH_CELL_FOOTPRINT = 1
```

## SDC file patterns

### Simple core-only design

```tcl
current_design my_design
set clk_name  core_clock
set clk_port  [get_ports clk]
set clk_period 25.0

create_clock -name $clk_name -period $clk_period $clk_port

set non_clock_inputs [all_inputs -no_clocks]
set_input_delay  [expr $clk_period * 0.2] -clock $clk_name $non_clock_inputs
set_output_delay [expr $clk_period * 0.2] -clock $clk_name [all_outputs]
```

### Full chip with IO pads

```tcl
current_design chip_top
set_units -time ns -resistance kOhm -capacitance pF -voltage V -current uA

set_max_fanout 8 [current_design]
set_max_capacitance 0.5 [current_design]
set_max_transition 3 [current_design]

create_clock [get_pins io_pad_clk/p2c] -name clk_core -period 20.0
set_clock_uncertainty 0.15 [get_clocks clk_core]
set_clock_transition 0.25 [get_clocks clk_core]

set_driving_cell -lib_cell sg13g2_IOPadIn -pin pad [all_inputs]
set_load -pin_load 5 [all_outputs]
```

## Debugging workflow

1. **Check timing after synthesis** -- Gross violations here mean unrealistic clock target or missing constraints
2. **Check after placement** -- Large WNS here may indicate placement congestion
3. **Check after CTS** -- Hold violations first appear here. If many hold violations, increase hold margin
4. **Check after routing** -- Final parasitics applied. This is the sign-off report
5. **If WNS negative at any stage**: Look at the critical path. Is it a real datapath or a false path? Is it caused by a high-fanout net or a long wire?
6. **If only a few paths fail**: SDC refinement (false paths, multicycle) is often the answer
7. **If many paths fail**: Clock period is too aggressive or utilization is too high
