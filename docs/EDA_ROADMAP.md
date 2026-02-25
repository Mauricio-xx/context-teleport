# Context Teleport for EDA/PDK: Domain Research and Roadmap

## Why this document

Context Teleport is feature-complete (459 tests, v0.3.0) but deployed in zero real projects. The tool was built generically, but the first real users are a PDK development team working on open-source semiconductor design kits (IHP SG13G2 130nm BiCMOS, SG13CMOS5L 5-metal CMOS). This document maps the EDA domain landscape, identifies what domain-specific tooling would be needed, and proposes a prioritized roadmap to bridge the gap between "generic context portability tool" and "useful in EDA/PDK daily work."

---

## 1. Domain landscape

### 1.1 IHP PDK ecosystem (the user's world)

| Repository | Purpose | Activity | Key pain points |
|------------|---------|----------|-----------------|
| **IHP-Open-PDK** (dev branch) | Main 130nm BiCMOS PDK: DRC, LVS, models, cells | 15 open issues, 14 open PRs | DRC false positives, LVS mismatches, xschem/KLayout alignment, device model drift |
| **ihp-sg13cmos5l** | Slim CMOS-only PDK (5 metal layers) | 14 branches, 4 PRs, 3 issues | Parallel feature dev (Magic, LibreLane, PCell rename), cross-branch coordination |
| **ihp-sg13g2-librelane-template** | RTL-to-GDS reference flow | Steady (pad integration, xschem frontend) | Nix environment setup, flow config tuning |
| **IHP-Open-PDK-docs** | Sphinx docs on ReadTheDocs | Incremental updates | Docs-to-implementation drift |
| **pycell4klayout-api** | Python PCell API for KLayout | Steady (callbacks, SG25H7) | Cross-PDK dependency |
| **ihp-gmid-kit** | gm/ID analog sizing toolkit | Active (Jupyter tutorials) | LUT generation, design space exploration |
| **ElemRV** | RISC-V with SpinalHDL + Renode co-sim | 63 commits on digital-twin branch | Co-simulation debugging, module deps |
| **testcases-cmos5l-ihp** | LibreLane RTL-to-GDS validation | Active | Flow reproducibility, timing closure |
| **IHP_A__BandgapReference_0xCD6E** | Analog IP reference design | Stable | Multi-tool workflow (xschem->SPICE->layout->DRC/LVS) |

### 1.2 Local project landscape

- **40+ projects** across `~/git/` and `~/personal_exp/`
- **20+ CLAUDE.md files** already encoding domain knowledge (flow configs, PDK gotchas, tool decisions)
- **Zero `.context-teleport/` bundles** deployed anywhere
- Most active WIP: `slim-pdk/ihp-sg13cmos5l` on branch `feature/cmos5l-librelane` (uncommitted changes)
- Rich knowledge already captured in CLAUDE.md: LibreLane parameter rationale, PDK limitations (no tapcells), DRC/LVS workarounds, tool version pinning

### 1.3 Existing MCP servers for EDA

| Server | What it does | Relevance |
|--------|-------------|-----------|
| **MCP4EDA** (NellyW8) | RTL-to-GDSII automation: Yosys, Icarus, LibreLane, KLayout, GTKWave | Direct competitor/complement -- covers flow execution, not context persistence |
| **OpenROAD MCP** (luarss) | Live Tcl session, timing reports, congestion maps, design space exploration | Complementary -- provides tool interaction, Context Teleport provides knowledge persistence |
| **SPICEBridge** | 18 tools: netlist creation, DC/AC/transient, schematic gen | Complementary -- simulation execution |
| **ngspice-mcp** | Direct ngspice interface | Complementary |
| **KiCAD MCP** | PCB layout + schematic via Claude/Cursor | Different domain (PCB vs IC) but same pattern |

**Key insight**: Existing MCP EDA servers handle tool execution (run DRC, simulate, place-and-route). None handle persistent knowledge, decision tracking, or cross-session context. This is exactly the gap Context Teleport fills.

### 1.4 AI + semiconductor industry trends

- **Keysight ML Toolkit** (Jan 2026): Parameter extraction 200+ steps to <10, model dev weeks to hours
- **Siemens EDA AI** (DAC 2025): Agentic AI for layout optimization, verification
- **LLM4EDA research** (ACM survey): HDL generation, script generation, test generation, verification
- **Claude + Diode/Zener**: PCB design via code-like DSL
- **IHP PDK**: No AI integration story yet -- greenfield opportunity

---

## 2. What agents actually need in EDA workflows

From analyzing the 20+ CLAUDE.md files and EDA artifacts across the user's projects, agent context in EDA falls into these categories:

### 2.1 Knowledge types (what to store in context bundles)

| Category | Examples | Source artifacts |
|----------|----------|-----------------|
| **PDK facts** | Process node, voltage domains (1.2V core / 3.3V IO), available libraries, layer stack | Tech files (.tech), LEF, Liberty |
| **Design rules** | Metal pitch, min width, spacing, via rules, density requirements | DRC rule files (.lydrc, .drc), PDK docs |
| **Tool chain config** | Which flow (LibreLane vs ORFS), which branch/version, stage overrides | config.yaml, config.mk, Makefile |
| **Known issues** | DRC false positives, missing cells (no tapcells in IHP), tool bugs with workarounds | GitHub issues, CLAUDE.md decision logs |
| **Design decisions** | Why core-only (LibreLane padring limitation), why CLOCK_PERIOD=20ns (conservative for 130nm), why disable antenna check | CLAUDE.md, PR discussions |
| **Device models** | Transistor parameters, resistor values, process corners (PVT) | SPICE models, Liberty timing, gm/ID LUTs |
| **Verification state** | Which DRC rules pass/fail, LVS match status, timing slack | Run logs, report files |
| **Flow parameters** | PDN pitch/width, placement density, routing layers, clock tree config | config.yaml (50-570 lines per design) |

### 2.2 Decision patterns (what to track as ADRs)

From the CLAUDE.md files, recurring decision categories:

1. **Flow selection**: LibreLane vs ORFS, core-only vs full-chip, specific branch/commit
2. **Parameter tuning**: Clock period, die area, PDN strategy, metal layer restrictions
3. **Tool workarounds**: Skip stages (antenna, Magic DRC), disable features (tapcell=0), manual cell mapping
4. **PDK adaptations**: Layer name conversions (Metal1 vs met1), cell library substitutions, device parameter overrides
5. **Verification waivers**: Which DRC warnings are acceptable, LVS exceptions, timing violations to accept

### 2.3 Skills (reusable agent capabilities for EDA)

Natural SKILL.md candidates from observed workflows:

| Skill | Description | Tools involved |
|-------|-------------|----------------|
| `run-drc` | Execute KLayout DRC on a design, parse results, identify real vs false-positive violations | KLayout, DRC rule files |
| `run-lvs` | Execute LVS comparison, parse mismatches, suggest fixes | KLayout/Magic, netlist tools |
| `debug-timing` | Analyze timing reports, identify critical paths, suggest SDC/config changes | OpenROAD, Liberty |
| `configure-pdn` | Design power delivery network given PDK constraints and die area | LibreLane config, PDK tech |
| `characterize-device` | Generate gm/ID lookup tables for a given transistor type | ngspice, ihp-gmid-kit |
| `port-design` | Adapt a design from one PDK to another (e.g., Sky130 to IHP) | Multiple (LEF, Liberty, tech files) |

---

## 3. Gap analysis: what Context Teleport lacks for EDA

### 3.1 What already works (no changes needed)

- Knowledge CRUD, decisions, skills -- all generic enough for EDA content
- Git-backed sync -- PDK teams already use git
- Cross-tool adapters -- Claude Code, Cursor, etc. all usable for EDA work
- Section-level merge -- useful for CLAUDE.md files with EDA knowledge
- Scope system -- public PDK knowledge vs private user notes vs ephemeral session state

### 3.2 Gaps to fill

| Gap | Severity | Description |
|-----|----------|-------------|
| **No EDA project detection** | High | Context Teleport doesn't know it's in a PDK project. Can't auto-discover config.yaml, tech files, DRC rules |
| **No artifact-aware import** | High | `import claude-code` reads CLAUDE.md. Nothing reads config.yaml, .tech files, or DRC reports to extract knowledge |
| **No structured decision categories** | Medium | Decisions are flat text. EDA needs categories: flow-selection, parameter-tuning, verification-waiver, pdk-adaptation |
| **No pre-built EDA skills** | Medium | Skills system exists but is empty. EDA teams need starter skills for common workflows |
| **No integration with EDA MCP servers** | Medium | MCP4EDA, OpenROAD MCP exist. Context Teleport could feed them knowledge or consume their outputs |
| **No run-state capture** | Low | After a DRC/LVS/PnR run, results aren't automatically captured as context |
| **No issue tracker bridge** | Low | GitHub issues encode decisions/knowledge but aren't imported into bundles |

---

## 4. Roadmap: prioritized phases

### Phase 1: EDA Skills Pack (standalone, no code changes to Context Teleport) -- DONE

**Goal**: Create a curated set of SKILL.md files for EDA workflows that can be added to any project via `context-teleport skill add`.

**Deliverables**:
- 8 SKILL.md files in `eda-skills-pack/skills/`: debug-drc, debug-lvs, debug-timing, configure-pdn, configure-librelane, characterize-device, xschem-simulate, port-design
- Each skill references IHP SG13G2 specifics but is structured to be adaptable to other PDKs
- Skills stored in a shareable git repo (separate from Context Teleport)

**Effort**: Small (content authoring, not engineering)

### Phase 2: EDA knowledge templates + pilot deployment -- DONE

**Goal**: Deploy Context Teleport in 2 real projects with pre-populated domain knowledge.

**Deployed projects**:

**1. IHP-Open-PDK** (`/home/montanares/git/slim-pdk/IHP-Open-PDK/`)
- Branch: `feature/context-teleport` (from `dev`)
- 12 knowledge entries (6 imported from CLAUDE.md/MEMORY.md + 6 manual: SG13CMOS5L layer reduction, device status, tech.json changes, DRM source of truth, manufacturing grid, no tap cells)
- 6 decision records (JSON layer management, TopMetal commenting strategy, device symlinks, CMOS-compatible resistors, GuardRing not standalone, DRM PDFs as authority)
- 8 EDA skills installed from pack
- MCP registered (--local), exported to `.claude/` and CLAUDE.md managed section

**2. LibreLane reference designs** (`/home/montanares/git/IHP-Open-DesignLib/LibreLane/`)
- Branch: `feature/context-teleport` (from `dev/librelane-setup`)
- Store at git root: `IHP-Open-DesignLib/.context-teleport/`
- 7 knowledge entries (1 imported from CLAUDE.md + 6 manual: design runtimes, config.json gotchas, Magic vs KLayout DRC, density expectations, pin placement patterns, tool version policy)
- 5 decision records (Nix reproducibility, IllegalOverlap nullify, absolute FP_SIZING, --no_density for reference, bus-only custom pins)
- 8 EDA skills installed from pack
- MCP registered (--local), exported to `.claude/` and CLAUDE.md managed section

**Sync validation**: Bare remotes at `~/personal_exp/ctx-remotes/`, push verified, clone verified, content matches.

**Lessons learned**:
- `find_project_root()` resolves to git root, not necessarily the subdirectory you're in (relevant for monorepos like IHP-Open-DesignLib)
- `.context-teleport/` must be gitignored at the git root level, not just in subdirectories
- Context stores need manual `git init` + remote add for sync; `push` alone only commits locally if no git is initialized
- DRM/layout rules PDFs (`libs.doc/doc/`) are the authoritative source of truth for both PDKs; any tooling references (layer_tracking/, editors) are secondary and may be outdated
- Never refer to SG13CMOS5L as "slim PDK"
- LibreLane and IHP PDK: always use `dev` branch, no pinned releases
- nix-eda: always latest available, no pinned versions

**Effort**: Small-medium (deployment + content curation)

### Phase 3: EDA project detector + artifact-aware import -- DONE

**Goal**: Teach Context Teleport to recognize EDA projects and extract knowledge from EDA-specific artifacts.

**Implementation**: New `src/ctx/eda/` package (separate from `AdapterProtocol` -- import-only, no export/MCP config).

**Deliverables**:

**3a. Project detector** (`src/ctx/eda/detect.py`):
- `detect_eda_project(root)` returns `EdaProjectInfo` with type, design name, PDK, markers, suggested skills
- Detects: LibreLane (config.json), ORFS (config.mk), PDK (libs.tech/), analog (xschemrc, *.sch)
- Auto-shows EDA info on `context-teleport init` and `context-teleport status`

**3b. EdaImporter protocol** (`src/ctx/eda/parsers/base.py`):
- `ImportItem` dataclass (type, key, content, source)
- `EdaImporter` protocol: `can_parse()`, `parse()`, `describe()`
- Registry: `auto_detect_importer(path)`, `get_importer(name)`, `list_importers()`

**3c. Six parsers** (`src/ctx/eda/parsers/`):
- **librelane-config**: LibreLane config.json (design params, flow stages, PDN, PDK overrides)
- **librelane-metrics**: state_in.json (synthesis, timing, DRC, LVS, routing, power metrics)
- **magic-drc**: Magic DRC .rpt (streaming parser for multi-million-line reports, counts per rule)
- **netgen-lvs**: Netgen LVS .rpt (cell equivalence, device counts, pin mismatches, final result)
- **orfs-config**: ORFS config.mk (Makefile variable extraction, category grouping, line continuations)
- **liberty**: Liberty .lib header (library name, PVT corner, units, defaults; directory mode for corner summary)

**3d. CLI integration** (`src/ctx/cli/adapter_cmd.py`):
- `context-teleport import eda <path> [--type TYPE] [--dry-run] [--format json]`
- Auto-detects importer via `can_parse()` cascade, or force with `--type`
- Writes via `store.set_knowledge()` with author `import:eda-<name> (<user>)`
- Re-import overwrites same key (latest run wins), history preserved in git

**Tests**: 106 new tests (parsers, detector, CLI integration). Full suite: 565 tests.

**Deferred to later**: Magic .tech parser, KLayout .lydrc parser (parsers for these formats can be added following the same EdaImporter pattern).

### Phase 4: Decision categories + structured templates

**Goal**: Add EDA-specific structure to the decision system.

**Deliverables**:
- Decision categories: `flow-selection`, `parameter-tuning`, `verification-waiver`, `pdk-adaptation`, `tool-workaround`
- Decision templates with pre-filled fields per category (e.g., `verification-waiver` template includes: rule name, violation count, justification, risk assessment)
- MCP tool update: `context_record_decision` accepts optional `category` parameter
- CLI: `context-teleport decision add --category verification-waiver`
- Search/filter by category: `context_search` returns category-filtered results

**Why fourth**: Requires schema consideration (v0.4.0?). Benefits from having real decisions in the system from Phase 2/3 to inform the category design.

**Effort**: Medium (schema extension, MCP/CLI updates, tests)

### Phase 5: MCP server federation (Context Teleport + EDA MCP servers)

**Goal**: Enable Context Teleport to work alongside MCP4EDA, OpenROAD MCP, and SPICEBridge.

**Strategy**: Start light, deepen as MCP federation patterns mature.

- **Phase 5a (light touch)**: Context Teleport stores knowledge independently. Agents read from both servers. Context Teleport exposes a `context://eda/pdk-summary` resource that any MCP client can read. No coupling to MCP4EDA internals.
- **Phase 5b (deeper, when ready)**: If MCP federation patterns emerge (server-to-server calls), Context Teleport becomes a "memory layer" that EDA MCP servers can query for PDK knowledge, design decisions, and verification state. This avoids agents re-discovering known information on every session.

**Why fifth**: Most ambitious. Depends on other MCP servers existing and being deployed. The integration pattern needs real usage data from earlier phases.

**Effort**: Large (cross-server coordination, prompt engineering, testing)

### Phase 6: GitHub issue bridge

**Goal**: Import knowledge and decisions from GitHub issue discussions into context bundles.

**Deliverables**:
- `context-teleport import github-issues --repo IHP-GmbH/IHP-Open-PDK --labels DRC,LVS`
- Parse issue titles, bodies, and key comments into knowledge entries
- Track issue resolution as decision records
- Periodic sync: new issues appear as knowledge, closed issues update status

**Why last**: Nice-to-have. Issues are already accessible via `gh` CLI. The value is in structured import, not access.

**Effort**: Medium (GitHub API integration, parsing heuristics)

### Phase 7:
Auto mejora y auto-update
---

## 5. Competitive positioning

### What Context Teleport offers that others don't

| Capability | MCP4EDA | OpenROAD MCP | SPICEBridge | Context Teleport |
|-----------|---------|-------------|-------------|-----------------|
| Run EDA tools | Yes | Yes | Yes | No (not its job) |
| Persistent knowledge across sessions | No | No | No | **Yes** |
| Team knowledge sharing | No | No | No | **Yes** (git sync) |
| Cross-tool context (Claude + Cursor + etc.) | No | No | No | **Yes** (adapters) |
| Decision tracking with rationale | No | No | No | **Yes** |
| Merge conflict resolution for context | No | No | No | **Yes** |
| Agent attribution | No | No | No | **Yes** |

### The pitch for EDA teams

"MCP4EDA runs your DRC. Context Teleport remembers which DRC rules are false positives, why you chose those flow parameters, and shares that knowledge with every agent on your team."

---

## 6. Resolved questions

1. **Skill pack distribution**: Separate git repo. Context Teleport should be aware of skill packs as an installable concept (future: `context-teleport skill install <pack-url>`).

2. **PDK versioning**: Deferred for long-term design. Short-term: add `pdk_version` field to bundle manifest (name + git ref). Knowledge entries can optionally carry `pdk_ref` tags. When PDK updates, diff against stored ref to flag stale entries. Full lifecycle design in Phase 3/4 with real usage data.

3. **Config parser scope**: Support all major formats -- LibreLane config.yaml, ORFS config.mk, Magic .tech files, KLayout .lydrc, Liberty .lib. Start narrow (LibreLane first), expand based on demand.

4. **MCP4EDA integration depth**: Light touch now (Phase 1-3), expose `context://eda/pdk-summary` resource in Phase 4-5, deeper federation only if MCP server-to-server patterns emerge. Avoid coupling to MCP4EDA's young API.
