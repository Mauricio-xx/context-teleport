# EDA Workflows

Context Teleport includes first-class support for Electronic Design Automation (EDA) projects. It can detect your project type, parse design artifacts into structured knowledge, and suggest relevant skills for your workflow.

## Project Detection

The `detect_eda_project()` function scans a directory for markers that indicate the type of EDA project. Detection is automatic when you run EDA-related commands.

### Supported Project Types

| Type | Markers | Description |
|---|---|---|
| **librelane** | `config.json` with `DESIGN_NAME` and `meta.version` 2 or 3 | LibreLane digital flow |
| **orfs** | `config.mk` with `DESIGN_NAME` or `PLATFORM` | OpenROAD Flow Scripts |
| **pdk** | `libs.tech/` directory | PDK development |
| **analog** | `xschemrc`, `.xschemrc`, or `*.sch` files | Analog/schematic design |

Detection also reads the `PDK_ROOT` environment variable as an additional marker and attempts to infer the PDK name from it.

### Suggested Skills per Project Type

When a project type is detected, Context Teleport suggests relevant skills from the EDA skills pack:

| Project Type | Suggested Skills |
|---|---|
| librelane | `configure-librelane`, `configure-pdn`, `debug-drc`, `debug-lvs`, `debug-timing` |
| orfs | `configure-pdn`, `debug-drc`, `debug-lvs`, `debug-timing` |
| pdk | `debug-drc`, `debug-lvs`, `port-design` |
| analog | `xschem-simulate`, `characterize-device`, `debug-drc`, `debug-lvs` |

## EDA Artifact Parsers

Context Teleport ships six parsers that convert EDA tool outputs into structured knowledge entries.

### Available Parsers

| Parser | Recognizes | Key Pattern |
|---|---|---|
| `librelane-config` | LibreLane JSON config (v2/v3) | `librelane-config-<design>` |
| `librelane-metrics` | LibreLane metrics JSON output | `librelane-metrics-<design>` |
| `magic-drc` | Magic DRC report files | `drc-summary-<design>` |
| `netgen-lvs` | Netgen LVS comparison results | `lvs-summary-<design>` |
| `orfs-config` | OpenROAD Flow Scripts config.mk | `orfs-config-<design>` |
| `liberty` | Liberty timing library files (.lib) | `liberty-summary-<library>` |

### Auto-Detection

When you do not specify `--type`, the CLI tries each parser in turn and uses the first one that reports it can handle the file. This works well for unambiguous file formats (e.g., a `.lib` file is always Liberty, a `config.json` with `meta.version` is always LibreLane).

If auto-detection fails, specify the parser explicitly with `--type`.

## Importing EDA Artifacts

### Basic Import

```bash
# Auto-detect parser
context-teleport import eda /path/to/config.json

# Force a specific parser
context-teleport import eda /path/to/report.txt --type magic-drc

# Preview what would be imported
context-teleport import eda /path/to/metrics.json --dry-run
```

### Key Naming and Re-Import

Each parser generates a deterministic key based on the design name extracted from the artifact. For example, importing a LibreLane config for design `inverter` produces the key `librelane-config-inverter`.

Re-importing the same artifact overwrites the existing entry with updated content. This is intentional: as your design iterates through synthesis, place-and-route, and signoff, you import updated artifacts and the knowledge store reflects the latest state.

### JSON Output

All import commands support `--format json` for scripting:

```bash
context-teleport import eda /path/to/config.json --format json
```

```json
{
  "items": [
    {"type": "knowledge", "key": "librelane-config-inverter", "source": "config.json"}
  ],
  "imported": 1,
  "dry_run": false,
  "importer": "librelane-config"
}
```

## Example: LibreLane Design with IHP SG13G2

This example walks through importing artifacts for a LibreLane digital design targeting the IHP SG13G2 PDK.

### 1. Initialize the Context Store

```bash
cd /path/to/my-librelane-project
context-teleport init my-inverter
```

### 2. Import the LibreLane Configuration

```bash
context-teleport import eda config.json
# Auto-detected: librelane-config
# Imported 1 item(s) via librelane-config
#   librelane-config-inverter <- config.json
```

The imported knowledge entry contains a structured summary of the configuration: design name, PDK, clock period, die area, pin placements, and key flow parameters.

### 3. Run DRC and Import Results

After running Magic DRC through the LibreLane flow:

```bash
context-teleport import eda results/signoff/inverter.drc
# Imported 1 item(s) via magic-drc
#   drc-summary-inverter <- inverter.drc
```

### 4. Run LVS and Import Results

```bash
context-teleport import eda results/signoff/inverter.lvs
# Imported 1 item(s) via netgen-lvs
#   lvs-summary-inverter <- inverter.lvs
```

### 5. Check Imported Knowledge

```bash
context-teleport knowledge list
# key                          scope    updated
# librelane-config-inverter    public   2025-06-15
# drc-summary-inverter         public   2025-06-15
# lvs-summary-inverter         public   2025-06-15
```

Now any AI agent connected via MCP has full visibility into the design configuration, DRC status, and LVS results. When the agent encounters a DRC violation, it can cross-reference the config to understand pin placements, die area constraints, and PDK-specific rules.

### 6. Re-Import After Iteration

After fixing DRC violations and re-running signoff:

```bash
context-teleport import eda results/signoff/inverter.drc
# Imported 1 item(s) via magic-drc
#   drc-summary-inverter <- inverter.drc
```

The entry is overwritten with the updated results. No duplicate keys accumulate.

## EDA Skills Pack

Context Teleport provides a separate git repository (`eda-skills-pack`) containing pre-built `SKILL.md` files for common EDA tasks. These skills teach AI agents how to:

- Configure LibreLane flows
- Set up power delivery networks
- Debug DRC violations
- Debug LVS mismatches
- Analyze timing reports
- Run xschem simulations
- Characterize devices
- Port designs across PDKs

To use the skills pack, clone it and import the skills into your project:

```bash
# Clone the skills pack
git clone https://github.com/your-org/eda-skills-pack.git /tmp/eda-skills-pack

# Import individual skills
context-teleport skill add debug-drc --file /tmp/eda-skills-pack/skills/debug-drc/SKILL.md
```

> **Note:** A future version will support `context-teleport skill install <pack-url>` for direct installation from a repository URL.
