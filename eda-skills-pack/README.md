# EDA Skills Pack for Context Teleport

A curated set of agent skills (SKILL.md files) for EDA/PDK workflows, targeting the IHP SG13G2 130nm BiCMOS PDK. Designed for use with [Context Teleport](https://github.com/montanares/agents_teleport).

## Skills included

| Skill | Description |
|-------|-------------|
| `debug-drc` | Debug KLayout DRC violations -- triage real errors vs false positives |
| `debug-lvs` | Debug KLayout LVS mismatches -- identify root causes and fixes |
| `debug-timing` | Analyze OpenROAD/OpenSTA timing reports -- fix setup/hold violations |
| `configure-pdn` | Configure power delivery network for LibreLane and ORFS flows |
| `configure-librelane` | Set up LibreLane RTL-to-GDS flow -- from minimal to full-chip |
| `characterize-device` | Generate and use gm/ID lookup tables for transistor sizing |
| `xschem-simulate` | xschem-to-ngspice simulation workflows for analog designs |
| `port-design` | Port designs between PDKs (Sky130 to IHP SG13G2 focus) |

## Installation

### Into a Context Teleport bundle

```bash
# From a project with an initialized context-teleport store
for skill_dir in /path/to/eda-skills-pack/skills/*/; do
  skill_name=$(basename "$skill_dir")
  context-teleport skill add "$skill_name" --file "$skill_dir/SKILL.md"
done
```

### Individual skill

```bash
context-teleport skill add debug-drc --file /path/to/eda-skills-pack/skills/debug-drc/SKILL.md
```

### Manual (without Context Teleport)

Copy the SKILL.md files directly into your agent's skill directory:
- Claude Code: `.claude/skills/<name>/SKILL.md`
- Cursor: `.cursor/rules/<name>/SKILL.md`
- OpenCode: `.opencode/skills/<name>/SKILL.md`

## PDK coverage

Skills reference IHP SG13G2 specifics (layer stack, design rules, device models, known issues) but are structured to be adaptable to other PDKs. Key IHP-specific details are clearly marked in each skill.

Covered tools and flows:
- **Verification**: KLayout DRC/LVS (IHP rule decks)
- **Digital flow**: LibreLane (primary), ORFS (secondary)
- **Analog flow**: xschem + ngspice
- **Device characterization**: pygmid, gmid (medwatt), ihp-gmid-kit
- **PDK porting**: Sky130 to IHP SG13G2 migration guide

## Structure

```
eda-skills-pack/
  README.md
  skills/
    debug-drc/SKILL.md
    debug-lvs/SKILL.md
    debug-timing/SKILL.md
    configure-pdn/SKILL.md
    configure-librelane/SKILL.md
    characterize-device/SKILL.md
    xschem-simulate/SKILL.md
    port-design/SKILL.md
```

Each SKILL.md uses YAML frontmatter (`name`, `description`) followed by markdown instructions. This format is compatible with Context Teleport's skill system and round-trip safe across all supported adapters.

## Contributing

To add a new skill:
1. Create a directory under `skills/<skill-name>/`
2. Write a `SKILL.md` with frontmatter and actionable instructions
3. Focus on what an AI coding agent needs to do the task (not general documentation)
4. Include IHP-specific details but structure for PDK-portability
