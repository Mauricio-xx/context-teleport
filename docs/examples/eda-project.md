# EDA Project

An IC design project using LibreLane with the IHP SG13G2 130nm BiCMOS PDK, demonstrating EDA artifact import, design decision tracking, and skill-assisted design iteration.

## Scenario

Carlos is designing a low-noise amplifier (LNA) using the IHP SG13G2 PDK. He uses LibreLane for the digital hardening flow and Claude Code as his agent tool. He wants to track design decisions, import flow artifacts as context, and use EDA-specific skills.

## Project setup

### Initialize

```bash
cd ~/designs/sg13g2-lna
context-teleport init --name sg13g2-lna
context-teleport register claude-code
```

### EDA project detection

Context Teleport auto-detects the EDA project type:

```bash
# The project has a LibreLane config.json
context-teleport status
```

Output shows:

```
Project: sg13g2-lna
EDA project detected: librelane
  Design: lna_top
  PDK: ihp-sg13g2
  Config: ./config.json
  Suggested skills: configure-librelane, configure-pdn, debug-drc, debug-lvs, debug-timing
```

## Importing EDA artifacts

### LibreLane configuration

```bash
context-teleport import eda config.json
```

This parses the LibreLane JSON config and creates a knowledge entry:

```
Imported: librelane-config-lna_top
  Design: lna_top
  PDK: ihp-sg13g2
  Die area: 200x200 um
  Core utilization: 45%
  Clock period: 10ns
```

### After a flow run -- import results

```bash
# Import DRC report
context-teleport import eda results/drc/lna_top.drc
# Imported: drc-summary-lna_top (15 violations, 3 categories)

# Import LVS report
context-teleport import eda results/lvs/lna_top.lvs
# Imported: lvs-summary-lna_top (MATCH)

# Import metrics
context-teleport import eda results/metrics.json
# Imported: librelane-metrics-lna_top (area, timing, utilization)
```

### Dry-run preview

```bash
context-teleport import eda results/drc/lna_top.drc --dry-run
# Shows what would be imported without writing
```

## Design iteration with agent

### Session 1: Initial flow run analysis

```
Carlos: "I just ran the LibreLane flow. Pull up the results."

Agent: [reads context://knowledge/librelane-config-lna_top]
       [reads context://knowledge/drc-summary-lna_top]
       [reads context://knowledge/lvs-summary-lna_top]

       Flow results for lna_top:
       - LVS: MATCH
       - DRC: 15 violations (3 metal spacing, 8 via enclosure, 4 density)
       - Timing: met with 0.3ns slack

       The via enclosure violations are likely from the power grid.
       Should I look at the PDN configuration?

Carlos: "Yes, and record the decision to increase via enclosure margins"

Agent: [calls context_record_decision(
           title="Increase via enclosure margins for IHP SG13G2",
           context="DRC shows 8 via enclosure violations in PDN area",
           decision="Add 0.05um extra enclosure on all via definitions in config.json",
           consequences="Slightly increased routing congestion, eliminates via DRC violations"
       )]
```

### Session 2: After fixing DRC

Carlos re-runs the flow and re-imports the artifacts:

```bash
# Re-import overwrites with updated results
context-teleport import eda results/drc/lna_top.drc
# Updated: drc-summary-lna_top (3 violations, 1 category -- density only)
```

```
Carlos: "DRC results after the fix?"

Agent: [reads context://knowledge/drc-summary-lna_top]
       Down to 3 violations, all density-related.
       The via enclosure issues are resolved.
       Density violations can be fixed with fill insertion.

Carlos: "Record that decision too"

Agent: [calls context_record_decision(
           title="Use automatic metal fill for density DRC",
           context="3 remaining DRC violations are all metal density",
           decision="Enable LibreLane metal fill step in config.json",
           consequences="Clean DRC, slight increase in parasitic capacitance"
       )]
```

## Importing issues from the PDK repo

Carlos imports relevant issues from the IHP Open PDK repository:

```bash
context-teleport import github --repo IHP-GmbH/IHP-Open-PDK \
    --labels sg13g2 --state closed --as-decisions --limit 10
```

This creates:

- Knowledge entries summarizing each issue
- Decision records for closed issues (with `--as-decisions`)

```
Imported 8 issues:
  github-issue-ihp-open-pdk-835: SG13G2 metal stack DRC rule update
  github-issue-ihp-open-pdk-812: Via resistance values corrected
  ...
  + 5 decision records from closed issues
```

Now the agent knows about relevant PDK updates and resolved issues.

## EDA skills in action

### Using a pre-built skill

If the EDA skills pack is installed:

```
Carlos: "I need to debug the timing violations on the clock path"

Agent: [reads context://skills/debug-timing]
       Following the debug-timing skill:
       1. Check the clock tree report...
       2. Identify the critical path...
       3. Review the constraint file...
```

### Creating a project-specific skill

```
Carlos: "Save a skill for our IHP SG13G2 PDN configuration"

Agent: [calls context_add_skill(
           name="sg13g2-pdn-config",
           description="Power delivery network configuration for IHP SG13G2 designs",
           instructions="## IHP SG13G2 PDN Guidelines\n\n### Metal Stack\n- TopMetal2: power ring\n- TopMetal1: horizontal stripes\n- Metal5: vertical stripes\n\n### Via Rules\n- Minimum enclosure: 0.1um (use 0.15um for margin)\n..."
       )]
```

## Project state tracking

```
Carlos: "Update the project state"

Agent: [calls context_update_state(
           current_task="Metal fill insertion and final DRC clean",
           blockers="Waiting for updated liberty file from PDK team"
       )]
```

## Final context snapshot

After several iterations:

```bash
context-teleport summary
```

```
Project: sg13g2-lna
Knowledge: 7 entries
  - librelane-config-lna_top
  - drc-summary-lna_top
  - lvs-summary-lna_top
  - librelane-metrics-lna_top
  - github-issue-ihp-open-pdk-835
  - github-issue-ihp-open-pdk-812
  - ...

Decisions: 4 recorded
  - Increase via enclosure margins for IHP SG13G2
  - Use automatic metal fill for density DRC
  - (2 from GitHub issues)

Skills: 2 available
  - sg13g2-pdn-config
  - debug-timing

Current task: Metal fill insertion and final DRC clean
Blockers: Waiting for updated liberty file from PDK team
```

## Key takeaways

| Practice | Benefit |
|----------|---------|
| EDA artifact import | Flow results become agent-readable context |
| Re-import on iteration | Context tracks latest results without stale data |
| Design decision records | ADRs capture why each design choice was made |
| GitHub issue import | PDK issues become searchable project knowledge |
| EDA-specific skills | Reusable procedures for common EDA tasks |
| Project detection | Auto-suggests relevant skills for the project type |
