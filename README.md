# Context Teleport

![Schema v0.3.0](https://img.shields.io/badge/schema-v0.3.0-blue)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-green)
![CI](https://github.com/Mauricio-xx/context-teleport/actions/workflows/ci.yml/badge.svg)

Portable, git-backed context store for AI coding agents.

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

## How it works

Context Teleport is an **MCP server**. After a one-time registration, your agent tool manages context autonomously -- you interact through natural language, not terminal commands.

```
1. Register         ctx register claude-code
                         |
2. Agent connects   Tool starts a session -> spawns ctx-mcp over stdio
                         |
3. Agent works      Reads dynamic onboarding -> uses 17 tools autonomously
                         |
4. Git sync         On shutdown, uncommitted changes are auto-pushed
```

The lifecycle in detail:

1. **Register once** -- `ctx register <tool>` writes the MCP config for your agent tool (Claude Code, OpenCode, Cursor, Gemini). This is the only time you touch the terminal.
2. **Agent spawns the server** -- when you open a session, the tool starts `ctx-mcp` automatically over stdio. The server detects the project, reads the store, and presents dynamic onboarding instructions.
3. **Agent uses tools directly** -- the agent sees 17 tools (`context_add_knowledge`, `context_sync_push`, `context_record_decision`, etc.), 8 resources, and 4 prompts. It reads and writes context as part of normal conversation.
4. **Git sync happens through the agent** -- the agent pushes/pulls via MCP tools. On server shutdown, uncommitted changes are auto-pushed as a safety net.

You never need to run `ctx` commands during normal usage. The CLI exists for setup and for operations outside of agent sessions.

## Quickstart

### 1. Install

```bash
# No installation needed -- uvx resolves on demand (recommended)
uvx context-teleport --help

# Or install from PyPI
pip install context-teleport
```

### 2. Initialize a context store

```bash
# Using uvx
uvx context-teleport init --name my-project

# Or if installed
ctx init --name my-project
```

### 3. Register MCP server for your agent tool

```bash
ctx register claude-code   # or: opencode, cursor, gemini
```

This writes the MCP config file for your tool (e.g. `.claude/mcp.json`). Done.

### 4. Start working

Open your agent tool and start a session. The agent has full access to the context store. Here is what a typical interaction looks like:

```
You: "Save that we're using hexagonal architecture with FastAPI"
Agent: [calls context_add_knowledge(key="architecture", content="...")]
       Done, saved to the team knowledge base.

You: "Record the decision to use PostgreSQL over SQLite"
Agent: [calls context_record_decision(title="Use PostgreSQL over SQLite", ...)]
       Decision recorded.

You: "Sync with the team"
Agent: [calls context_sync_push(message="Add architecture knowledge and DB decision")]
       Pushed 2 changes to remote.
```

The agent reads onboarding context automatically at session start, so returning to a project picks up right where you left off.

## Installation

### uvx (recommended, no install needed)

[uvx](https://docs.astral.sh/uv/) resolves and runs `context-teleport` on demand. Nothing to install or maintain.

```bash
uvx context-teleport init --name my-project
uvx context-teleport register claude-code
```

After registration, the MCP server config uses `uvx` as the command, so your agent tool resolves the package automatically on every session.

### pip install from PyPI

```bash
pip install context-teleport

ctx init --name my-project
ctx register claude-code
```

### From source (for development)

```bash
git clone https://github.com/Mauricio-xx/context-teleport.git
cd context-teleport
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Use --local flag to register with a local entry point instead of uvx
ctx register claude-code --local
```

## Team setup

Context Teleport is built for teams. Each person registers the MCP server once; the agents handle sync from there.

### Person A: initialize shared context

```bash
cd my-project
ctx init --name my-project --repo-url git@github.com:team/my-project.git
ctx register claude-code
```

Then in the agent session:

```
You: "Document that we're using FastAPI with hexagonal architecture"
Agent: [calls context_add_knowledge(key="architecture", content="...")]

You: "Record the decision to use PostgreSQL over SQLite"
Agent: [calls context_record_decision(title="Use PostgreSQL over SQLite", ...)]

You: "Push context to the team"
Agent: [calls context_sync_push(message="Initial project context")]
       Pushed to remote.
```

### Person B: join and start working

```bash
cd my-project    # already has the git remote
ctx register claude-code
```

Then open the agent tool. At session start, the server presents onboarding with all existing team context. Person B is immediately caught up.

```
You: "Add deployment knowledge: Docker Compose for local, k8s for prod"
Agent: [calls context_add_knowledge(key="deployment", content="...")]

You: "Push"
Agent: [calls context_sync_push(message="Add deployment knowledge")]
```

### Handling conflicts

If two people edit the same context file, the agent resolves it:

```
You: "Pull latest context"
Agent: [calls context_sync_pull(strategy="agent")]
       Conflict detected in knowledge/architecture.md.
       [calls context_conflict_detail(file_path="knowledge/architecture.md")]
       I see both versions. Person A added API guidelines, you added caching notes.
       These are in different sections, so I'll merge them.
       [calls context_resolve_conflict(file_path="...", content="...merged...")]
       [calls context_merge_finalize()]
       Merge complete. Both changes preserved.
```

Section-level merge handles most cases automatically -- conflicts only surface when two agents edit the same section of the same file.

## MCP server reference

The MCP server is the primary interface. It exposes the full context store to any MCP-compatible agent over stdio transport.

### Registration

```bash
ctx register claude-code   # writes .claude/mcp.json
ctx register opencode      # writes opencode.json
ctx register cursor        # writes .cursor/mcp.json
ctx register gemini        # writes .gemini/settings.json

# Auto-detect and register all available tools
ctx register
```

### Manual MCP configuration

If you prefer to configure MCP manually instead of using `ctx register`:

**Claude Code** (`.claude/mcp.json`):
```json
{
  "mcpServers": {
    "context-teleport": {
      "command": "uvx",
      "args": ["context-teleport"],
      "type": "stdio",
      "env": { "MCP_CALLER": "mcp:claude-code" }
    }
  }
}
```

**OpenCode** (`opencode.json`):
```json
{
  "mcpServers": {
    "context-teleport": {
      "command": "uvx",
      "args": ["context-teleport"],
      "type": "stdio",
      "env": { "MCP_CALLER": "mcp:opencode" }
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "context-teleport": {
      "command": "uvx",
      "args": ["context-teleport"],
      "type": "stdio",
      "env": { "MCP_CALLER": "mcp:cursor" }
    }
  }
}
```

**Gemini** (`.gemini/settings.json`):
```json
{
  "mcpServers": {
    "context-teleport": {
      "command": "uvx",
      "args": ["context-teleport"],
      "type": "stdio",
      "env": { "MCP_CALLER": "mcp:gemini" }
    }
  }
}
```

The `MCP_CALLER` env var is used for agent attribution -- it tags knowledge entries and decisions with the agent that wrote them.

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

### Prompts

| Prompt | Description |
|--------|-------------|
| `context_onboarding` | Full project context for a new agent session. Public knowledge, decisions, state, recent history. |
| `context_handoff` | Session handoff summary for the next agent. Current task, blockers, progress, recent sessions. |
| `context_review_decisions` | All architectural decisions with status, context, and consequences. |
| `context_resolve_conflicts` | Step-by-step guide for resolving merge conflicts via MCP tools, with per-file summaries. |

## CLI reference

The CLI is available for setup and for operations outside of agent sessions. All commands support `--format json` for machine-readable output.

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
| `ctx watch` | Monitor store and auto-commit/push on changes |
| `ctx config get\|set\|list` | Manage global configuration (default strategy, default scope) |

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
| **Gemini** | `.gemini/rules/*.md`, `.gemini/STYLEGUIDE.md`, `GEMINI.md` | `.gemini/rules/ctx-*.md` | `.gemini/settings.json` |
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

## Git sync and conflict resolution

Context sync uses git as the transport layer. Push stages only public files, commits, and pushes. Pull fetches and merges.

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
1. context_sync_pull(strategy="agent")
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

# Optional: install watchdog for ctx watch
pip install -e ".[watch]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and the PR process.

All contributions require signing the [CLA](CLA.md).

## License

AGPL-3.0-or-later. Contributions require a CLA.
