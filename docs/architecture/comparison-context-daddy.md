# context-teleport vs context-daddy: Comparative Analysis

This document compares [context-teleport](https://github.com/montanares/agents_teleport) and
[context-daddy](https://github.com/chipflow/context-daddy) (by ChipFlow/Robert Taylor).

Both solve the problem of AI agents losing context between sessions, but with fundamentally
different philosophies.

---

## Summary

| Dimension | context-teleport | context-daddy |
|---|---|---|
| **Philosophy** | Curated, persistent, shared knowledge | Auto-derived, ephemeral artifacts |
| **Scope** | Multi-tool (5 adapters), multi-agent, team | Claude Code only, single-user |
| **Storage** | Markdown + JSON sidecars (git-friendly) | SQLite + markdown + JSON (partially gitignored) |
| **MCP** | 32 tools, 16 resources, 4 prompts (FastMCP) | 12 tools, 0 resources, 0 prompts (low-level SDK) |
| **Git sync** | Section-level 3-way merge, conflict resolution | None |
| **Tests** | 930+ | Minimal (shell scripts) |
| **License** | AGPL-3.0 | MIT |
| **Data model** | Pydantic v2, schema migrations | Ad hoc, no formal models |

---

## Conceptual Overlaps

Both projects:

- Maintain a project context store exposed via MCP stdio
- Generate onboarding summaries for new agents
- Re-orient agents after context loss (compaction, restart)
- Use the project filesystem as backing store (no external service)
- Aim to reduce raw grep/find over source code

---

## Key Differences

### What gets stored

- **context-teleport**: Curated content (knowledge, decisions, conventions, skills, activity). Everything is intentional.
- **context-daddy**: Derived artifacts (symbol index via tree-sitter, AI-generated narrative from git log). Almost nothing is manually written.

### Team model

- **context-teleport**: Multi-tool (5 adapters), multi-agent, git sync with section-level merge, public/private/ephemeral scoping, agent attribution, activity board.
- **context-daddy**: Single-user, Claude Code only, no sync, no team model.

### Agent intervention

- **context-teleport**: Passive -- MCP server is available, the agent decides when to use it. Lifecycle hooks remind agents after compaction and inject context into subagents.
- **context-daddy**: Active -- lifecycle hooks (PreCompact, Stop, PreToolUse) intercept and redirect agent behavior. The Stop hook can block the agent until it reads context files.

### Code navigation

- **context-teleport**: Full-text search over the context store only (`.context-teleport/`), not source code.
- **context-daddy**: Full AST index of source code (tree-sitter for C++/Rust, ast stdlib for Python). Symbols with file path, line number, signature, docstring.

---

## What context-daddy has that we adopted

### Lifecycle hooks for Claude Code (implemented)

Hooks generated during `context-teleport register claude_code`:

- **PreCompact**: reminds agent to use context tools after compaction
- **SessionStart (compact)**: directs agent to `context_onboarding` prompt
- **SubagentStart**: injects project context awareness into subagents

Deliberately excluded: the "block Claude" Stop hook pattern (too aggressive).

### Markdown navigation tools (implemented)

Three new MCP tools that expose structured markdown navigation:

- `context_outline(key)` -- section headings with level and line number
- `context_get_section(key, heading)` -- extract a specific section by heading
- `context_list_tables(key)` -- find and extract markdown tables

These reuse the existing `parse_sections()` from the section-level merge engine.

### Enriched project manifest (implemented)

Auto-detection of languages and build systems during `init`:

- Detects 20+ marker files (pyproject.toml, Cargo.toml, CMakeLists.txt, package.json, etc.)
- Populates `languages` and `build_systems` fields in the manifest
- Surfaced in onboarding instructions as "Project stack"
- Backward compatible (old manifests default to empty lists)

---

## What context-daddy has that we chose not to adopt

### Code symbol indexing

Tree-sitter extracts functions, classes, variables with path, line, signature. Powerful but:

- Requires tree-sitter as dependency, subprocess isolation, watchdog, incremental cache
- Significant scope creep, changes the project's nature
- Better suited as a separate complementary MCP server

### AI-generated narrative from git history

"Story So Far", "Dragons & Gotchas" derived from `git log`. Useful for onboarding in unfamiliar codebases, but:

- Requires API key or spawning Claude CLI
- context-daddy uses `claude -p --dangerously-skip-permissions` (security concern)
- May be better as an explicit `context-teleport import narrative` command

---

## What we have that context-daddy does not

- Git sync with section-level 3-way merge
- 5 bidirectional adapters (Claude Code, Cursor, Gemini, OpenCode, Codex)
- Typed models (Pydantic v2) with schema migrations
- Scoping (public/private/ephemeral) via sidecars
- Skills with auto-improvement pipeline (usage, feedback 1-5, proposals, upstream PR)
- Conventions as first-class content type
- ADR-style decisions with status lifecycle
- Activity board (check-in/check-out, staleness detection)
- Agent attribution (MCP_CALLER)
- LLM-native conflict resolution
- 6 EDA parsers (domain-specialized)
- GitHub issue bridge
- 930+ tests
- Proper Python package (hatchling, CLI dual-mode)
- Dotpath uniform access
- Full-text search over the store
