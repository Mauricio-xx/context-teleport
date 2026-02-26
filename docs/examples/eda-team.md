# EDA Team: IHP SG13G2 PDK Support

Four engineers supporting the IHP SG13G2 130nm BiCMOS PDK collaborate across different agent tools on a shared context store. They are preparing designs for an MPW shuttle run, where a PDK fix discovered by one engineer ripples into another's design flow -- shared context makes the impact visible and actionable across tools.

- **Lukas** -- Claude Code: PDK cell library, device characterization, model updates
- **Amira** -- Cursor: LibreLane design flow, chip tapeout, timing closure
- **Jan** -- Gemini: DRC/LVS rule development, verification
- **Sofia** -- OpenCode: Analog design (xschem), bandgap and LNA simulation

## Setup

### Lukas initializes the project

```bash
cd ~/designs/sg13g2-shuttle
context-teleport init --name sg13g2-shuttle --repo-url git@github.com:team/sg13g2-shuttle.git
context-teleport register claude-code
```

### The team joins

```bash
# Amira
cd ~/designs/sg13g2-shuttle
context-teleport register cursor

# Jan
cd ~/designs/sg13g2-shuttle
context-teleport register gemini

# Sofia
cd ~/designs/sg13g2-shuttle
context-teleport register opencode
```

### Import baseline PDK issues

The team pulls in closed issues from the IHP Open PDK repo so every agent starts with known PDK errata and resolved fixes:

```bash
context-teleport import github --repo IHP-GmbH/IHP-Open-PDK \
    --state closed --labels sg13g2 --as-decisions --limit 15
```

```
Imported 12 issues:
  github-issue-ihp-open-pdk-835: SG13G2 metal stack DRC rule update
  github-issue-ihp-open-pdk-812: Via resistance values corrected
  github-issue-ihp-open-pdk-798: pnpMPA model parameter fix
  ...
  + 9 decision records from closed issues
```

### Load EDA skills from the skills pack

```bash
context-teleport skill add debug-drc --file eda-skills-pack/debug-drc/SKILL.md
context-teleport skill add debug-lvs --file eda-skills-pack/debug-lvs/SKILL.md
context-teleport skill add configure-pdn --file eda-skills-pack/configure-pdn/SKILL.md
context-teleport skill add xschem-simulate --file eda-skills-pack/xschem-simulate/SKILL.md
context-teleport sync push -m "Baseline: PDK issues + EDA skills"
```

## Day 1-2: Independent work with cross-pollination

### Lukas (Claude Code) -- Via resistance discovery

Lukas characterizes via resistances and finds that the published values for via5 (TopMetal1 to Metal5) are wrong.

```
Lukas: "I measured via5 resistance across 20 test structures. The PDK
        model says 2.8 ohm but I'm consistently seeing 4.5 ohm. Record this."

Agent: [calls context_add_knowledge(
           key="via5-resistance-measurement",
           content="## Via5 (TopMetal1-Metal5) Resistance\n\nMeasured: 4.5 ohm/via
           (20 structures, wafer lot W24-103)\nPDK model value: 2.8 ohm/via\n
           Delta: +60% -- significant for high-current PDN paths.\n\n
           Source: 4-point Kelvin measurement on MPW-2024Q3 silicon."
       )]
       Saved. (author: mcp:claude-code)

Lukas: "Record the decision to use the corrected value going forward"

Agent: [calls context_record_decision(
           title="Use measured via5 resistance (4.5 ohm) over PDK model value",
           context="via5 resistance measured at 4.5 ohm vs 2.8 ohm in PDK model.
                    60% higher than expected, affects PDN IR-drop and timing.",
           decision="All shuttle designs must use 4.5 ohm/via for via5 in IR-drop
                     analysis. File errata with IHP.",
           consequences="PDN designs need more vias or wider straps to meet IR-drop
                         budget. Timing signoff margins may tighten."
       )]

Lukas: "Push"
Agent: [calls context_sync_push(message="Via5 resistance errata and corrected value")]
```

This is the ripple that propagates through the team.

### Amira (Cursor) -- LibreLane flow and the ripple effect

Amira runs the LibreLane flow for her top-level design and imports the results:

```bash
context-teleport import eda config.json
# Imported: librelane-config-shuttle_top

context-teleport import eda results/drc/shuttle_top.rpt
# Imported: drc-summary-shuttle_top (7 violations, 2 categories)

context-teleport import eda results/lvs/shuttle_top.rpt
# Imported: lvs-summary-shuttle_top (MATCH)

context-teleport import eda results/metrics.json
# Imported: librelane-metrics-shuttle_top (area, timing, utilization)
```

Then she pulls context and gets the via resistance update:

```
Amira: "Pull context and check for anything new"

Agent: [calls context_sync_pull()]
       Pulled. New from Lukas (claude-code):
         - via5-resistance-measurement
         - Decision: Use measured via5 resistance (4.5 ohm)

       [reads context://knowledge/via5-resistance-measurement]
       [reads context://knowledge/librelane-config-shuttle_top]

       Important: The via5 resistance is 60% higher than the PDK model.
       Your PDN uses via5 for TopMetal1-to-Metal5 power connections.
       With the corrected value, IR-drop on VDD increases from 12mV to
       ~19mV -- close to your 20mV budget.

       I recommend tightening the PDN strap pitch to compensate.

Amira: "Good catch. Tighten the Metal5 strap pitch from 30um to 20um
        and record the decision."

Agent: [calls context_record_decision(
           title="Tighten Metal5 PDN strap pitch from 30um to 20um",
           context="Via5 resistance errata (4.5 vs 2.8 ohm) pushes IR-drop
                    from 12mV to ~19mV against 20mV budget",
           decision="Reduce Metal5 vertical strap pitch from 30um to 20um in
                     pdn.tcl. Increases via5 count per strap intersection.",
           consequences="IR-drop margin restored to ~13mV. Routing utilization
                         increases by ~5%, acceptable at current 52%."
       )]
       [calls context_sync_push(message="PDN strap tightening for via5 errata")]
```

This is the core cross-domain moment: a PDK measurement in Claude Code produced a design flow decision in Cursor, with full traceability.

### Jan (Gemini) -- DRC rule update

Jan receives a foundry bulletin with updated Metal5 density requirements:

```
Jan: "New density rules from IHP bulletin 2024-Q3-07. Metal5 min density
      goes from 20% to 25%, max stays at 75%. Record it."

Agent: [calls context_add_knowledge(
           key="sg13g2-metal5-density-rules",
           content="## Metal5 Density Rules (Bulletin 2024-Q3-07)\n\n
           - Minimum density: 25% (was 20%)\n- Maximum density: 75%\n
           - Window size: 100x100 um\n- Effective: all tapeouts after 2024-10-01"
       )]

Jan: "Are there other metal stack entries I should know about?"

Agent: [calls context_search(query="metal stack via resistance")]
       Found: via5-resistance-measurement (from claude-code)
       The via5 resistance is 60% higher than the model. This may
       affect DRC rules for via density near power connections.

Jan: "Good, I'll factor that into the via density check rules."
Agent: [calls context_sync_push(message="Metal5 density rules from foundry bulletin")]
```

### Sofia (OpenCode) -- Analog characterization

Sofia is simulating a bandgap reference circuit. She pulls context and evaluates the via resistance impact:

```
Sofia: "Pull context and summarize what's new"

Agent: [calls context_sync_pull()]
       Updates from the team:
       - Lukas: via5 resistance errata (4.5 ohm vs 2.8 ohm)
       - Amira: PDN strap pitch tightened for IR-drop
       - Jan: Metal5 density rules updated

       For your bandgap circuit: via5 resistance mainly affects
       high-current digital paths. Your bandgap reference current
       is ~10uA, so the IR-drop through via5 is <0.05mV.
       Negligible for your design.

Sofia: "Agreed. Record the pnpMPA characterization results instead."

Agent: [calls context_add_knowledge(
           key="pnpmpa-characterization-w24103",
           content="## pnpMPA Characterization (Wafer W24-103)\n\n
           - Beta: 3.2 (spec: 3.0 typ)\n- Vbe @ 10uA: 648mV @ 27C\n
           - Ideality factor: 1.02\n- CTAT slope: -1.78 mV/C\n
           Consistent with updated model from PDK issue #798."
       )]
       [calls context_sync_push(message="pnpMPA characterization results")]
```

## Day 4: The conflict

Lukas and Jan both update the metal stack reference knowledge at the same time. Lukas adds TopMetal2 slit rules, Jan adds the density bounds.

### Lukas pushes first

```
Lukas: "Add TopMetal2 slit rules to the metal stack reference"

Agent: [calls context_add_knowledge(
           key="sg13g2-metal-stack-reference",
           content="...existing content...\n\n## TopMetal2 Slit Rules\n
           - Required for widths > 10um\n- Slit width: 2um\n
           - Slit spacing: 8um\n- Applies to power bus routing"
       )]
       [calls context_sync_push(message="TopMetal2 slit rules")]
       Pushed.
```

### Jan's push fails

```
Jan: "Add the updated density bounds to the metal stack reference"

Agent: [calls context_add_knowledge(
           key="sg13g2-metal-stack-reference",
           content="...existing content...\n\n## Metal Density Bounds\n
           - Metal5: 25-75%\n- TopMetal1: 20-80%\n- TopMetal2: 30-70%\n
           - Window: 100x100um for all layers"
       )]
       [calls context_sync_push(message="Metal density bounds")]
       Error: push failed, remote has changes.

Jan: "Pull and resolve"

Agent: [calls context_sync_pull(strategy="agent")]
       Conflict in knowledge/sg13g2-metal-stack-reference.md.

       [calls context_conflict_detail(
           file_path=".context-teleport/knowledge/sg13g2-metal-stack-reference.md"
       )]
       Lukas added a "TopMetal2 Slit Rules" section,
       you added a "Metal Density Bounds" section.
       These are in different ## sections -- merging cleanly.

       [calls context_resolve_conflict(
           file_path="...", content="...merged with both sections..."
       )]
       [calls context_merge_finalize()]
       Merged. Both TopMetal2 slit rules and density bounds preserved.
```

Section-level merge handled this automatically because the changes were in different `## ` sections of the same file.

## Week 2: Skill evolution

After several flow runs, Jan and Amira find that the `debug-drc` skill is missing guidance on IHP-specific filler cell density rules -- a common stumbling block.

### Rating and feedback

```
Jan: "The debug-drc skill doesn't mention IHP filler density workarounds.
      That's the first thing I check. Rate it 2."

Agent: [calls context_rate_skill(name="debug-drc", rating=2,
           comment="Missing IHP filler density workaround for Metal5 25% minimum")]
```

```
Amira: "Same issue. I spent 30 minutes before realizing I needed FILL_INSERTION.
        Rate it 3."

Agent: [calls context_rate_skill(name="debug-drc", rating=3,
           comment="Should include FILL_INSERTION step for IHP density DRC")]
```

### Identifying the problem

```bash
context-teleport skill stats --sort rating
```

```
Name              Usage  Avg Rating  Attention
debug-drc             7        2.5   !!
debug-lvs             4        4.2
configure-pdn         5        3.8
xschem-simulate       3        4.0
```

The `debug-drc` skill is flagged as needing attention.

### Proposing an improvement

```
Jan: "Propose an improvement to debug-drc that adds the IHP filler density
      workaround as a dedicated section."

Agent: [calls context_propose_skill_improvement(
           name="debug-drc",
           proposed_content="## Debug DRC Failures\n\n...existing steps...\n\n
           ## IHP SG13G2 Density Workarounds\n\n### Metal Fill Insertion\n
           If density violations appear on Metal5 (min 25%):\n
           1. Enable `FILL_INSERTION: true` in LibreLane config\n
           2. Set `FILL_CONFIG` to point to `sg13g2_fill.json`\n
           3. Re-run from floorplan stage\n\n
           ### Filler Cell Placement\n
           For standard cell density:\n
           1. Verify filler cells are in the cell library\n
           2. Check `PLACE_DENSITY` is above 0.6\n
           3. Run `detailed_placement` with `-filler` flag",
           rationale="Two team members rated this skill poorly because IHP
                      density DRC is the most common failure mode and the
                      existing skill doesn't cover it at all."
       )]
       Proposal created: a1b2c3d4
```

### Accepting the proposal

The team lead reviews and accepts:

```bash
context-teleport skill proposals --skill debug-drc
# ID          Status   Agent        Rationale (truncated)
# a1b2c3d4   pending  mcp:gemini   Two team members rated poorly...

context-teleport skill apply-proposal debug-drc a1b2c3d4
# Applied proposal a1b2c3d4 to debug-drc
# Diff: +18 lines (new section: IHP SG13G2 Density Workarounds)
```

### Creating a project-specific skill

Lukas creates a shuttle-specific checklist from the team's accumulated experience:

```
Lukas: "Create a skill for our MPW shuttle pre-tapeout checklist"

Agent: [calls context_add_skill(
           name="mpw-shuttle-checklist",
           description="Pre-tapeout checklist for IHP SG13G2 MPW shuttle",
           instructions="## MPW Shuttle Pre-Tapeout Checklist\n\n
           ### PDK Errata\n- [ ] via5 resistance: use 4.5 ohm (not 2.8)\n
           - [ ] pnpMPA model: verify W24-103 parameters applied\n\n
           ### DRC\n- [ ] Metal5 density >= 25% (bulletin 2024-Q3-07)\n
           - [ ] TopMetal2 slit rules for widths > 10um\n
           - [ ] FILL_INSERTION enabled\n\n
           ### IR-Drop\n- [ ] PDN analysis with corrected via resistances\n
           - [ ] Metal5 strap pitch <= 20um\n- [ ] VDD drop < 20mV\n\n
           ### Signoff\n- [ ] DRC clean\n- [ ] LVS match\n
           - [ ] Liberty corners regenerated with updated models"
       )]
       [calls context_sync_push(message="MPW shuttle checklist skill")]
```

## Session handoff

At the end of the day, Amira wraps up and Lukas picks up where she left off.

### Amira closes out

```
Amira: "Wrap up my session. I finished the PDN rework but timing
        closure on the clock tree still needs another iteration."

Agent: [calls context_update_state(
           current_task="Timing closure on shuttle_top clock tree",
           blockers="Hold time violations on scan chain after PDN rework"
       )]
       [calls context_append_session(
           agent="cursor",
           summary="Completed PDN strap rework (Metal5 pitch 30->20um).
                    IR-drop now 13mV. Re-ran STA -- setup timing clean,
                    but 3 hold violations on scan chain path.",
           knowledge_added="librelane-config-shuttle_top (updated)",
           decisions_added="Tighten Metal5 PDN strap pitch"
       )]
       [calls context_sync_push(message="Amira EOD: PDN rework complete, hold violations remain")]
```

### Lukas picks up

```
Lukas: "What's the current status? I'm picking up from Amira."

Agent: [uses context_handoff prompt]
       Amira (cursor) finished the PDN strap rework -- Metal5 pitch
       is now 20um, IR-drop is 13mV (under the 20mV budget).

       Remaining blocker: 3 hold time violations on the scan chain
       path after the PDN rework. Setup timing is clean.

       Current task: timing closure on shuttle_top clock tree.
```

## Final snapshot

After two weeks, the shared context store captures the full team's work:

```bash
context-teleport summary
```

```
Project: sg13g2-shuttle
Knowledge: 14 entries
  - via5-resistance-measurement         (mcp:claude-code)
  - sg13g2-metal-stack-reference        (mcp:claude-code, mcp:gemini)
  - sg13g2-metal5-density-rules         (mcp:gemini)
  - pnpmpa-characterization-w24103      (mcp:opencode)
  - librelane-config-shuttle_top        (mcp:cursor)
  - drc-summary-shuttle_top             (mcp:cursor)
  - lvs-summary-shuttle_top             (mcp:cursor)
  - librelane-metrics-shuttle_top       (mcp:cursor)
  - github-issue-ihp-open-pdk-835       (cli)
  - github-issue-ihp-open-pdk-812       (cli)
  - ...4 more from PDK issues

Decisions: 8 recorded
  - Use measured via5 resistance (4.5 ohm)
  - Tighten Metal5 PDN strap pitch from 30um to 20um
  - (6 from GitHub issues)

Skills: 6 available
  - debug-drc (improved)
  - debug-lvs
  - configure-pdn
  - xschem-simulate
  - mpw-shuttle-checklist
  - sg13g2-pdn-config

Current task: Timing closure on shuttle_top clock tree
Blockers: Hold time violations on scan chain after PDN rework
```

## Key takeaways

| Pattern | Implementation |
|---------|---------------|
| Cross-domain propagation | PDK via resistance fix (Claude Code) triggers PDN strap decision (Cursor) |
| EDA artifact import | LibreLane config, DRC, LVS, metrics imported as structured knowledge |
| GitHub issue bridge | Closed PDK issues imported as decisions for team baseline |
| 4-tool collaboration | Claude Code, Cursor, Gemini, OpenCode sharing one context store |
| Section-level merge | Simultaneous metal stack updates auto-merged by section |
| Skill feedback loop | `debug-drc` rated poorly, improved via proposal, accepted by team lead |
| Project-specific skill | MPW shuttle checklist distilled from team experience |
| Agent attribution | Every entry tagged with originating tool via `MCP_CALLER` |
