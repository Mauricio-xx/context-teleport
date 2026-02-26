# Context Scoping

Context Teleport provides three scope levels that control how entries are stored, synced, and exported. Scoping applies uniformly to knowledge entries, decisions, and skills.

## Scope Levels

| Scope | Synced via git | Exported to adapters | Persists across sessions |
|---|---|---|---|
| **public** (default) | Yes | Yes | Yes |
| **private** | No (gitignored) | No | Yes |
| **ephemeral** | No (gitignored) | No | No (cleared on state reset) |

### Public

Public entries are the default. They are committed to git, pushed to remotes, and included when exporting context to any adapter (Claude Code, Cursor, Gemini, etc.). Use public scope for anything the entire team or all agents should see.

Typical public entries:

- Architecture documentation
- Shared ADRs (Architecture Decision Records)
- Team coding conventions
- Reusable skills

### Private

Private entries stay on the local machine. They are gitignored and excluded from exports. The entry files themselves never leave your workstation, but the `.scope.json` metadata file **is** synced so collaborators know the entry exists (just not its content).

Typical private entries:

- Personal workflow notes
- Machine-specific configuration paths
- Local tool preferences

> **Warning:** Private scope is not a secrets manager. Do not store API keys, tokens, or credentials in Context Teleport. Use `.env` files or a dedicated secrets vault for that.

### Ephemeral

Ephemeral entries behave like private entries but are additionally cleared when you run `context-teleport state clear`. They exist only for the duration of a working session.

Typical ephemeral entries:

- Scratch analysis results
- Temporary debugging notes
- Session-specific context that should not accumulate

## Setting Scope

### Via CLI

Each entry type has a `scope` subcommand:

```bash
# Knowledge
context-teleport knowledge scope architecture-overview public
context-teleport knowledge scope my-local-notes private
context-teleport knowledge scope scratch-analysis ephemeral

# Decisions
context-teleport decision scope 3 private

# Skills
context-teleport skill scope debug-drc public
```

You can also set scope at creation time with the `--scope` flag:

```bash
context-teleport knowledge set local-paths "..." --scope private
context-teleport skill add my-workflow --scope ephemeral
```

### Via MCP

Agents can change scope programmatically using the `context_set_scope` tool:

```json
{
  "entry_type": "knowledge",
  "key": "architecture-overview",
  "scope": "public"
}
```

The `entry_type` parameter accepts `knowledge`, `decision`, or `skill`.

### Via Global Configuration

You can change the default scope for all new entries:

```bash
context-teleport config set default_scope private
```

Valid values: `public`, `private`, `ephemeral`. The default is `public` if not configured.

## How Scope Is Stored

Scope metadata lives in `.scope.json` sidecar files, one per directory (`knowledge/`, `knowledge/decisions/`, `skills/`). The sidecar stores only non-public entries -- public scope is the implicit default when a key is absent from the file.

Example `.scope.json`:

```json
{
  "local-paths": "private",
  "scratch-analysis": "ephemeral"
}
```

The sidecar files themselves are always committed and synced. This means collaborators can see which keys have restricted scope, even though they cannot see the content of those entries.

## Push and Export Behavior

### Git Push

When `context-teleport push` (or auto-sync via `watch`) runs, only public files are staged for commit. Private and ephemeral files are excluded from `git add`. The `.scope.json` sidecar is always staged so the scope map propagates to the team.

### Adapter Export

When exporting to an adapter (e.g., `context-teleport export claude-code`), only public entries are written to the adapter's files. Private and ephemeral entries are silently skipped.

### Listing with Scope Filter

All `list` commands support a `--scope` filter:

```bash
context-teleport knowledge list --scope private
context-teleport decision list --scope public
context-teleport skill list --scope ephemeral
```

## Example Workflow

A developer sets up a project with shared architecture docs and personal notes:

```bash
# Initialize the store
context-teleport init my-project

# Add shared knowledge (public by default)
context-teleport knowledge set architecture "## Architecture\n\nMicroservices with event bus..."
context-teleport knowledge set coding-standards "## Standards\n\nUse black for formatting..."

# Add personal notes (private, not synced)
context-teleport knowledge set my-todo "Things I need to check tomorrow" --scope private

# Add session scratch (ephemeral, cleared on reset)
context-teleport knowledge set debug-session "Current stack trace analysis..." --scope ephemeral

# Verify scopes
context-teleport knowledge list
# key              scope      updated
# architecture     public     2025-06-15
# coding-standards public     2025-06-15
# debug-session    ephemeral  2025-06-15
# my-todo          private    2025-06-15

# Push to remote -- only public entries are staged
context-teleport push

# Export to Claude Code -- only public entries exported
context-teleport export claude-code

# Later, clear ephemeral data
context-teleport state clear
# debug-session is gone; my-todo and public entries remain
```

## Scope and Multi-Agent Collaboration

When multiple agents work on the same project through different adapters, scope controls what each agent sees:

- **Public entries** are available to all agents after export.
- **Private entries** remain invisible to agents using other workstations.
- **Ephemeral entries** are invisible to everyone after a session ends.

This makes scope useful for separating concerns: shared project knowledge stays public, while agent-specific working memory can be ephemeral so it does not pollute the shared context over time.
