# Changelog

All notable changes to Context Teleport are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.5] - 2026-03-04

### Added
- **Plugin system for domain importers**: `ctx.importers` entry-point group allows third-party packages to register artifact importers without forking the repo
- `ArtifactImporter` protocol in `ctx.importers.base` as the public API for plugin authors
- Lazy registry merging built-in EDA parsers with entry-point discovered plugins (broken plugins logged and skipped, name collisions warned)
- All 6 EDA parsers registered as `ctx.importers` entry points in pyproject.toml
- `context-teleport import artifacts` CLI command with `--list`, `--type`, `--dry-run`
- Warning-level logging across all adapters and MCP registration for silent failure paths (missing directories, JSON parse errors, git failures)
- OpenCode agent definition import from `.opencode/agents/` (with nested path support)
- OpenCode command definition import from `.opencode/commands/`
- Decisions export to AGENTS.md managed section for OpenCode adapter
- `opencode_data_dir()` utility respecting OPENCODE_DATA_DIR and XDG_DATA_HOME

### Fixed
- `__version__` mismatch (`0.5.4` -> `0.5.5`) now matches pyproject.toml
- Unused `import pytest` lint error in test_opencode.py
- Plugin registry suppresses shadow warnings when entry-point resolves to the same class as a built-in (no noise in installed environments)
- "No importer recognized" error replaced with actionable message: "No plugin found. You might need to install a third-party importer for this file format."
- OpenCode session import: replaced broken SQLite reader with JSON file reading from actual data directory
- OpenCode sessions now imported as knowledge entries instead of being silently discarded

### Documentation
- Replaced stale SQLite session references with JSON sessions, `.opencode/agents/`, `.opencode/commands/` across all adapter docs
- Documented `import artifacts` CLI command in reference, EDA workflows, and EDA parsers pages
- Documented plugin system (`ctx.importers` entry-point group) in EDA parsers reference and contributing guide
- Retitled "Adding EDA Parsers" to "Adding Domain Importers" with third-party plugin guide, `ArtifactImporter` protocol, `pyproject.toml` entry-point examples
- Updated adapter-pattern diagram: OpenCode import sources, Plugin Registry box
- Updated architecture-overview diagram: MCP counts (32 tools, 16 resources, 4 prompts), Plugin Registry in Domain box

### Removed
- SQLite dependency from OpenCode adapter (was reading wrong path, wrong schema)

## [0.5.4] - 2026-03-02

### Added
- MCP registration schema contract tests validating configs against each tool's real JSON schema
- JSON schemas for Claude Code, Cursor, Gemini, and OpenCode MCP config formats
- Schema contract check added to release gate (check 8)
- `jsonschema` dev dependency for contract validation

## [0.5.3] - 2026-03-01

### Added
- MCP prompt count contract tests and payload shape E2E assertions
- CLI/MCP parity tests verifying identical store side-effects across interfaces
- Adapter export-import round-trip tests for all 5 adapters
- CHANGELOG.md in Keep a Changelog format
- Context governance reference doc with all limits and thresholds
- Release gate in CI (CHANGELOG, minimum test count, schema version consistency)

### Fixed
- Bash arithmetic bug in release-check.sh (`set -e` incompatibility)
- Unused import lint error in test_detect.py

## [0.5.2] - 2025-06-10

### Added
- Lifecycle hooks for Claude Code (PreCompact, SessionStart, SubagentStart)
- Markdown navigation tools (`context_list_headings`, `context_read_section`)
- Project auto-detection during `init` (languages, build systems, EDA markers)
- Session history cap (200 entries) to prevent unbounded growth
- Onboarding content truncation (2000 chars per entry)
- `release-check.sh` pre-release validation script
- Contract tests for MCP tool/resource counts vs source and docs

### Fixed
- Documentation alignment: tool, resource, prompt counts now match source
- Stale activity entries excluded from onboarding instructions

## [0.5.1] - 2025-06-05

### Added
- Auto-initialization of context store when MCP server starts in a git repo
- Staging safety: `_get_stageable_files()` restricts commits to `.context-teleport/`

### Fixed
- Lint errors in older modules

## [0.5.0] - 2025-05-28

### Added
- Team conventions as first-class content type (`conventions/<key>.md`)
- Team activity board for cross-agent awareness (`activity/<member>.json`)
- Convention export to all 5 adapters (Claude Code, Cursor, Gemini, OpenCode, Codex)
- CLI commands: `convention list/get/add/rm/scope`, `activity list/check-in/check-out`
- MCP tools for conventions (4) and activity (2), resources (3)
- Onboarding instructions include conventions and active team members
- Dotpath support for `conventions` and `activity` namespaces

## [0.4.0] - 2025-05-20

### Added
- Skill auto-improvement: usage tracking, feedback (1-5 ratings), improvement proposals
- Sidecar files per skill (`.usage.ndjson`, `.feedback.ndjson`, `.proposals/`)
- MCP tools: `context_report_skill_usage`, `context_rate_skill`, `context_propose_skill_improvement`, `context_list_skill_proposals`
- CLI commands: `skill stats`, `skill feedback`, `skill review`, `skill proposals`, `skill apply-proposal`, `skill propose-upstream`
- Instructions flag skills needing review (avg rating < 3.0)
- Schema migration 0.3.0 -> 0.4.0 (no-op, sidecar files created lazily)

## [0.3.0] - 2025-05-12

### Added
- Section-level merge for markdown files (3-way merge at `## ` header granularity)
- 5 adapter ecosystem: Claude Code, Cursor, Gemini, OpenCode, Codex
- Agent attribution (`KnowledgeEntry.agent`, `MCP_CALLER` env var)
- Context scoping (public/private/ephemeral) with `.scope.json` sidecars
- LLM-based conflict resolution via MCP delegation (Strategy.agent)
- Agent Skills (`SKILL.md`) as first-class content type with YAML frontmatter
- Shared frontmatter parser extracted from Cursor MDC format
- EDA domain: project detection, 6 artifact parsers, 8-skill pack
- GitHub issue bridge: import issues as knowledge/decisions via `gh` CLI
- Schema migration 0.2.0 -> 0.3.0 (backward compatible)

## [0.2.0] - 2025-05-01

### Added
- Git sync engine with push/pull/conflict detection/resolution
- MCP server with FastMCP (tools, resources, prompts over stdio)
- CLI via typer with subcommands for knowledge, decisions, sync, import, export
- Bundle versioning and migration framework
- Interactive conflict resolution CLI
- MCP registration commands for agent tools

## [0.1.0] - 2025-04-20

### Added
- Initial release: core context store with knowledge entries and decisions
- `ContextStore` API for CRUD operations on `.context-teleport/` bundle
- Search across knowledge and decisions
- AGPL-3.0 license
