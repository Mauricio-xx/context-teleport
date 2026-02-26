# EDA Parsers

Context Teleport includes import-only parsers for common EDA (Electronic Design Automation) artifact formats. These parsers read EDA-specific files and produce structured knowledge entries for the context store.

## EdaImporter protocol

Defined in `src/ctx/eda/parsers/base.py`:

```python
@runtime_checkable
class EdaImporter(Protocol):
    name: str

    def can_parse(self, path: Path) -> bool:
        """Check if this importer can handle the given path."""

    def parse(self, path: Path) -> list[ImportItem]:
        """Parse the artifact at path and return knowledge items."""

    def describe(self) -> str:
        """Human-readable description of what this importer handles."""
```

### ImportItem

```python
@dataclass
class ImportItem:
    type: str    # "knowledge"
    key: str     # e.g. "librelane-config-inverter"
    content: str # markdown body
    source: str  # human-readable file path
```

!!! info "Import-only"
    Unlike `AdapterProtocol` (bidirectional, models AI coding tools), `EdaImporter` is import-only: it reads EDA-specific files and produces knowledge entries. No export, no MCP config.

## Built-in parsers

### LibreLane Config (`librelane-config`)

Parses LibreLane JSON configuration files (meta.version 2 or 3).

| Field | Value |
|-------|-------|
| **Input** | `config.json` with `DESIGN_NAME` and `meta.version` 2 or 3 |
| **Key pattern** | `librelane-config-<design-name>` |
| **Extracts** | Design name, PDK, die area, core utilization, clock period, pin placements, power nets |

```bash
context-teleport import eda config.json --type librelane-config
```

### LibreLane Metrics (`librelane-metrics`)

Parses LibreLane flow metrics JSON output.

| Field | Value |
|-------|-------|
| **Input** | Metrics JSON from LibreLane flow runs |
| **Key pattern** | `librelane-metrics-<design-name>` |
| **Extracts** | Area, utilization, timing slack, wire length, cell counts, DRC/LVS pass/fail |

```bash
context-teleport import eda metrics.json --type librelane-metrics
```

### Magic DRC (`magic-drc`)

Parses Magic DRC (Design Rule Check) report files.

| Field | Value |
|-------|-------|
| **Input** | Magic DRC report text files |
| **Key pattern** | `drc-summary-<design-name>` |
| **Extracts** | Total violations, violation categories, counts per rule, pass/fail status |

```bash
context-teleport import eda design.drc --type magic-drc
```

### Netgen LVS (`netgen-lvs`)

Parses Netgen LVS (Layout vs. Schematic) report files.

| Field | Value |
|-------|-------|
| **Input** | Netgen LVS comparison report text files |
| **Key pattern** | `lvs-summary-<design-name>` |
| **Extracts** | Match/mismatch status, device counts, net counts, pin mismatches, property errors |

```bash
context-teleport import eda design.lvs --type netgen-lvs
```

### ORFS Config (`orfs-config`)

Parses OpenROAD Flow Scripts `config.mk` files.

| Field | Value |
|-------|-------|
| **Input** | `config.mk` with `DESIGN_NAME` or `PLATFORM` |
| **Key pattern** | `orfs-config-<design-name>` |
| **Extracts** | Design name, platform/PDK, die area, core utilization, clock period, Verilog sources |

```bash
context-teleport import eda config.mk --type orfs-config
```

### Liberty (`liberty`)

Parses Liberty (.lib) timing library files.

| Field | Value |
|-------|-------|
| **Input** | `.lib` Liberty timing files |
| **Key pattern** | `liberty-summary-<library-name>` |
| **Extracts** | Library name, process/voltage/temperature, cell count, cell list with function/area summaries |

```bash
context-teleport import eda sg13g2_stdcell.lib --type liberty
```

## EDA project detection

The `detect_eda_project()` function (`src/ctx/eda/detect.py`) scans a directory for markers that indicate the type of EDA project.

### Detected project types

| Type | Markers | Suggested skills |
|------|---------|-----------------|
| `librelane` | `config.json` with `DESIGN_NAME` and `meta.version` 2/3 | configure-librelane, configure-pdn, debug-drc, debug-lvs, debug-timing |
| `orfs` | `config.mk` with `DESIGN_NAME` or `PLATFORM` | configure-pdn, debug-drc, debug-lvs, debug-timing |
| `pdk` | `libs.tech/` directory | debug-drc, debug-lvs, port-design |
| `analog` | `xschemrc` or `.sch` files | xschem-simulate, characterize-device, debug-drc, debug-lvs |

Additional marker: `PDK_ROOT` environment variable is noted if present.

### EdaProjectInfo

```python
@dataclass
class EdaProjectInfo:
    detected: bool = False
    project_type: str = ""     # "librelane", "orfs", "pdk", "analog"
    design_name: str = ""
    pdk: str = ""
    config_path: str = ""
    markers_found: list[str] = field(default_factory=list)
    suggested_skills: list[str] = field(default_factory=list)
```

## CLI usage

### Auto-detect parser

```bash
# Auto-detect file type and import
context-teleport import eda config.json

# Preview without writing
context-teleport import eda config.json --dry-run
```

### Explicit parser type

```bash
# Force a specific parser
context-teleport import eda report.txt --type magic-drc
```

### Re-import behavior

Re-importing the same artifact overwrites the existing knowledge entry with the same key. This allows updating context as design iterations proceed without accumulating stale entries.

## Parser registry

The parser registry (`src/ctx/eda/parsers/__init__.py`) maintains the list of all available parsers. Auto-detection iterates through all registered parsers and uses the first one where `can_parse()` returns `True`.

To add a new parser, see [Adding EDA Parsers](../contributing/adding-eda-parsers.md).
