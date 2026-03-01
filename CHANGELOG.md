# Changelog

All notable changes to Context Teleport are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
