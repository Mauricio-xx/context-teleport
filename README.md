# Context Teleport

Portable, git-backed context store for AI coding agents.

Schema v0.3.0 | Python 3.11+ | AGPL-3.0

---

## The problem

AI coding agents accumulate deep context over sessions -- architecture decisions, codebase knowledge, workflow preferences, task progress. That context is trapped in tool-specific formats on a single machine. There is no standard way to move it between devices, share it across a team, or use it with a different agent tool. Every time you switch machines or onboard a teammate, the agent starts from zero.

## What Context Teleport does

- **Portable context bundle** -- structured store for knowledge, decisions, state, preferences, and session history
- **Git-backed sync** -- push/pull context to any git remote, works like code sync
- **Section-level merge** -- 3-way merge at markdown section granularity, reduces false conflicts in multi-agent workflows
- **Cross-tool adapters** -- import/export between Claude Code, OpenCode, Codex, Gemini, and Cursor
- **MCP server** -- 17 tools, 8 resources, 4 prompts; works with any MCP-compatible agent
- **Context scoping** -- public (team), private (user-only), ephemeral (session-only) boundaries
- **Agent attribution** -- tracks which agent wrote each entry
- **LLM-based conflict resolution** -- agents can inspect and resolve merge conflicts via MCP tools

## Quickstart

```bash
# Install
pip install -e .

# Initialize a context store in your project
ctx init --name my-project

# Add knowledge
ctx knowledge set architecture "Python monolith, PostgreSQL, Redis cache"
ctx knowledge set tech-stack "Python 3.12, FastAPI, SQLAlchemy 2.0"

# Record a decision
ctx decision add "Use SQLAlchemy 2.0 async"

# Check what you have
ctx summary

# Push to git remote
ctx push

# On another machine, pull context
ctx pull

# Register MCP server for your agent tool
ctx register claude-code
```

## CLI reference

All commands support `--format json` for machine-readable output.

### Top-level commands

| Command | Description |
|---------|-------------|
| `ctx init` | Initialize context store (`--name`, `--repo-url`) |
| `ctx status` | Show store state, sync status, adapter info |
| `ctx get <dotpath>` | Read any value by dotpath (e.g. `knowledge.architecture`) |
| `ctx set <dotpath> <value>` | Write any value by dotpath |
| `ctx search <query>` | Full-text search across all context (`--json`) |
| `ctx summary` | One-page context summary for LLM context windows |
| `ctx push` | Stage, commit, and push context changes (`-m`) |
| `ctx pull` | Pull remote context and merge (`-s ours\|theirs\|interactive\|agent`) |
| `ctx diff` | Show context changes (`--remote`) |
| `ctx log` | Show context change history (`--oneline`, `-n`) |
| `ctx register [tool]` | Register MCP server (auto-detects if no tool specified) |
| `ctx unregister [tool]` | Remove MCP server registration |

### `ctx knowledge`

| Command | Description |
|---------|-------------|
| `knowledge list` | List entries (`--scope public\|private\|ephemeral`) |
| `knowledge get <key>` | Read entry content |
| `knowledge set <key> [content]` | Write/update entry (accepts `--file`, stdin) |
| `knowledge rm <key>` | Delete entry |
| `knowledge scope <key> <scope>` | Change entry scope |
| `knowledge search <query>` | Full-text search within knowledge |

### `ctx decision`

| Command | Description |
|---------|-------------|
| `decision list` | List decision records (`--scope`) |
| `decision get <id\|title>` | Read a decision by ID or title match |
| `decision add <title>` | Create ADR (opens `$EDITOR`, or `--file`, or stdin) |

### `ctx state`

| Command | Description |
|---------|-------------|
| `state show` | Show current session state |
| `state set <key> <value>` | Update state field (`current_task`, `blockers`, or custom) |
| `state clear` | Reset ephemeral session state |

### `ctx sync`

| Command | Description |
|---------|-------------|
| `sync push` | Stage, commit, push (`-m` for message) |
| `sync pull` | Pull and merge (`-s` for strategy) |
| `sync resolve` | Retry merge with strategy (`-s ours\|theirs`) |
| `sync diff` | Show changes (`--remote` to compare with remote) |
| `sync log` | Show context commit history (`--oneline`, `-n`) |

### `ctx import` / `ctx export`

```bash
ctx import claude-code    # Extract from Claude Code into store
ctx import opencode       # Import from OpenCode
ctx import codex          # Import from Codex
ctx import gemini         # Import from Gemini
ctx import cursor         # Import from Cursor
ctx import bundle <path>  # Import a .ctxbundle archive

ctx export claude-code    # Inject store into Claude Code locations
ctx export opencode       # Export to OpenCode (AGENTS.md)
ctx export codex          # Export to Codex (AGENTS.md)
ctx export gemini         # Export to Gemini (.gemini/rules/)
ctx export cursor         # Export to Cursor (.cursor/rules/)
ctx export bundle <path>  # Export as portable .ctxbundle archive
```

All import/export commands support `--dry-run` to preview changes.

## MCP server

The MCP server exposes the full context store to any MCP-compatible agent over stdio transport.

### Starting the server

```bash
# Direct (stdio transport)
ctx-mcp

# Register with a specific tool
ctx register claude-code   # writes .claude/mcp.json
ctx register opencode      # writes opencode.json
ctx register cursor        # writes .cursor/mcp.json

# Auto-detect and register all available tools
ctx register
```

### Resources

| URI | Description |
|-----|-------------|
| `context://manifest` | Project metadata and configuration |
| `context://knowledge` | All knowledge entries with scopes |
| `context://knowledge/{key}` | Single knowledge entry by key |
| `context://decisions` | All decisions with status and scope |
| `context://decisions/{id}` | Single decision by ID or title |
| `context://state` | Current active session state |
| `context://history` | Recent session history |
| `context://summary` | High-level project context summary |

### Tools

#### Knowledge management

| Tool | Parameters | Description |
|------|-----------|-------------|
| `context_search` | `query` | Search across all context files. Returns ranked results with file, line, text, score. |
| `context_add_knowledge` | `key`, `content`, `scope?` | Add or update a knowledge entry. Scope: `public`/`private`/`ephemeral`. |
| `context_remove_knowledge` | `key` | Remove a knowledge entry by key. |
| `context_get` | `dotpath` | Read any value by dotpath (e.g. `knowledge.architecture`, `decisions.1`, `manifest.project.name`). |
| `context_set` | `dotpath`, `value` | Set a value by dotpath. |

#### Decisions

| Tool | Parameters | Description |
|------|-----------|-------------|
| `context_record_decision` | `title`, `context?`, `decision?`, `consequences?`, `scope?` | Record an ADR-style architectural decision. |

#### State and history

| Tool | Parameters | Description |
|------|-----------|-------------|
| `context_update_state` | `current_task?`, `blockers?` | Update the active session state. Blockers are comma-separated. |
| `context_append_session` | `agent?`, `summary?`, `knowledge_added?`, `decisions_added?` | Append a session summary to history. |

#### Scoping

| Tool | Parameters | Description |
|------|-----------|-------------|
| `context_get_scope` | `entry_type`, `key` | Get scope of a knowledge entry or decision. `entry_type`: `knowledge` or `decision`. |
| `context_set_scope` | `entry_type`, `key`, `scope` | Change scope. Values: `public`, `private`, `ephemeral`. |

#### Git sync

| Tool | Parameters | Description |
|------|-----------|-------------|
| `context_sync_push` | `message?` | Commit and push context changes. Auto-generates commit message if empty. |
| `context_sync_pull` | `strategy?` | Pull from remote. Strategy: `ours` (default), `theirs`, `agent`. Use `agent` for LLM-based resolution. |

#### Conflict resolution

| Tool | Parameters | Description |
|------|-----------|-------------|
| `context_merge_status` | -- | Check for unresolved merge conflicts (disk-persisted state). |
| `context_conflict_detail` | `file_path` | Get full ours/theirs/base content, unified diff, and section analysis for markdown files. |
| `context_resolve_conflict` | `file_path`, `content` | Resolve a single file by providing final merged content. |
| `context_merge_finalize` | -- | Apply all resolutions and commit the merge. Falls back to `ours` for unresolved files. |
| `context_merge_abort` | -- | Abort the pending merge and discard conflict state. |

### Prompts

| Prompt | Description |
|--------|-------------|
| `context_onboarding` | Full project context for a new agent session. Public knowledge, decisions, state, recent history. |
| `context_handoff` | Session handoff summary for the next agent. Current task, blockers, progress, recent sessions. |
| `context_review_decisions` | All architectural decisions with status, context, and consequences. |
| `context_resolve_conflicts` | Step-by-step guide for resolving merge conflicts via MCP tools, with per-file summaries. |

## Bundle structure

```
.context-teleport/
  manifest.json                    # Project name, schema version, adapter config
  .gitignore                       # Auto-generated: excludes private/ephemeral + local state
  knowledge/
    *.md                           # Knowledge entries (one file per key)
    .scope.json                    # Scope sidecar: maps filenames to private/ephemeral
    .meta.json                     # Author metadata per entry
    decisions/
      0001-decision-title.md       # ADR-style decision records
      .scope.json
  state/
    active.json                    # Current task, blockers, progress (gitignored)
    roadmap.json                   # Project roadmap
  preferences/
    team.json                      # Team preferences (synced via git)
    user.json                      # User preferences (gitignored)
  history/
    sessions.ndjson                # Append-only session log
```

## Adapters

| Tool | Imports from | Exports to | MCP registration |
|------|-------------|-----------|-----------------|
| **Claude Code** | `MEMORY.md`, `CLAUDE.md`, `.claude/rules/*.md` | `CLAUDE.md` managed section, `MEMORY.md` | `.claude/mcp.json` |
| **OpenCode** | `AGENTS.md`, `.opencode/opencode.db` (sessions) | `AGENTS.md` managed section | `opencode.json` |
| **Codex** | `AGENTS.md`, `.codex/instructions.md` | `AGENTS.md` managed section | Not supported |
| **Gemini** | `.gemini/rules/*.md`, `.gemini/STYLEGUIDE.md`, `GEMINI.md` | `.gemini/rules/ctx-*.md` | Not supported |
| **Cursor** | `.cursor/rules/*.mdc` (MDC format), `.cursorrules` | `.cursor/rules/ctx-*.mdc` | `.cursor/mcp.json` |

Export writes only public-scope entries. Import attributes each entry with `import:<tool>` as the author.

## Context scoping

Every knowledge entry and decision has a scope that controls visibility and sync behavior.

| Scope | Synced via git | Visible to team | Exported | Use case |
|-------|---------------|-----------------|----------|----------|
| `public` | Yes | Yes | Yes | Architecture docs, shared decisions, team knowledge |
| `private` | No (gitignored) | No | No | Personal notes, local machine config |
| `ephemeral` | No (gitignored) | No | No | Session-only scratch data, cleared on `state clear` |

Scopes are stored in `.scope.json` sidecar files. Content files are not modified -- scope is pure metadata. The default scope is `public`.

```bash
# Set scope on a knowledge entry
ctx knowledge scope my-notes private

# Filter by scope
ctx knowledge list --scope public

# Set scope via MCP
context_set_scope(entry_type="knowledge", key="my-notes", scope="private")
```

## Git sync and conflict resolution

Context sync uses git as the transport layer. `ctx push` stages only public files, commits, and pushes. `ctx pull` fetches and merges.

### Merge strategies

| Strategy | Behavior |
|----------|----------|
| `ours` | Keep local version on conflict (default) |
| `theirs` | Take remote version on conflict |
| `interactive` | TUI prompts for each conflicted file |
| `agent` | Expose conflicts via MCP tools for LLM-based resolution |

### Section-level merge

For markdown files, Context Teleport performs 3-way merge at the `## ` section level before falling back to file-level strategy. If two agents edited different sections of the same file, the merge auto-resolves without conflict.

### Agent conflict resolution flow

When using `strategy=agent`, the workflow is:

```
1. ctx pull --strategy agent
   (or context_sync_pull(strategy="agent") via MCP)
   -> Returns conflict report, persisted to disk

2. context_conflict_detail(file_path)
   -> Full content of ours/theirs/base, unified diff, section analysis

3. context_resolve_conflict(file_path, content)
   -> Provide merged content for each file

4. context_merge_finalize()
   -> Commit the merge, clear conflict state
```

Conflict state is persisted to `.context-teleport/.pending_conflicts.json` (gitignored), so it survives across MCP calls and stateless tool invocations. Use `context_merge_abort()` to discard and start over.

## Development

```bash
# Install with dev dependencies
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests (374 tests)
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## License

AGPL-3.0-or-later. Contributions require a CLA.
