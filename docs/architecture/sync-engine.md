# Sync Engine

How Context Teleport uses git for synchronization, including push/pull internals, section-level merge, and conflict resolution strategies.

![Sync and Conflict Resolution](../assets/sync-conflict.svg)

## Overview

Context Teleport uses git as its transport layer. The `GitSync` class (`src/ctx/sync/git_sync.py`) wraps git operations and adds:

- **Scope-aware staging**: Only public files are staged for push
- **Section-level merge**: Markdown files merge at `## ` section granularity
- **Multi-strategy conflict resolution**: ours, theirs, interactive, agent
- **Persistent conflict state**: Survives across MCP calls for agent-based resolution

## Push flow

```
context_sync_push(message="Add architecture knowledge")
    |
    v
GitSync.push()
    |
    1. Scope filter -- read .scope.json, exclude private/ephemeral files
    2. Stage filtered files -- git add (only public content)
    3. Commit -- auto-generate message if empty
    4. Push -- git push to remote (if remote exists)
    |
    v
Result: {"status": "pushed"} or {"status": "committed"} (no remote)
```

If there is no remote configured, push still commits locally and returns `{"status": "committed"}`. This means the sync tools work in offline/local-only scenarios.

## Pull flow

```
context_sync_pull(strategy="ours")
    |
    v
GitSync.pull()
    |
    1. Fetch from remote -- git fetch
    2. Attempt merge -- git merge
    |
    +-- Clean merge? --> Done: {"status": "pulled"}
    |
    +-- Conflicts?
        |
        +-- Try section-level merge for .md files
        |   |
        |   +-- All sections resolved? --> Done
        |   +-- Conflicts remain? --> Fall through to strategy
        |
        +-- Apply strategy
            |
            +-- ours: keep local version
            +-- theirs: take remote version
            +-- interactive: TUI prompt per file
            +-- agent: persist state, return conflict report
```

## Section-level merge

The key innovation in Context Teleport's sync is section-level merge for markdown files (`src/ctx/core/merge_sections.py`).

### How it works

Instead of treating the entire file as a unit, the merge engine:

1. **Parses** base, ours, and theirs versions into sections (split on `## ` headers)
2. **Compares** each section independently using content equality
3. **Merges** section by section:
   - Section unchanged in both: keep as-is
   - Section changed in only one side: take the changed version
   - Section changed in both sides: conflict (only for this section)
   - New sections: include from whichever side added them

### Why this matters

Without section-level merge, two agents editing different parts of `knowledge/architecture.md` would produce a file-level conflict:

```
Agent A adds "## API Guidelines" section
Agent B adds "## Caching Strategy" section
  --> File-level conflict (both modified the same file)
```

With section-level merge, these auto-resolve because the changes are in different sections.

### Implementation details

- Trailing whitespace is normalized via `_content_eq()` to avoid false conflicts from section boundary shifts
- Sections are identified by `## ` prefix (level-2 headers)
- Content before the first `## ` header is treated as a "preamble" section
- Integration point: `GitSync.pull()` calls `_try_section_merge()` before falling back to file-level strategy

## Conflict resolution strategies

### `ours` (default)

Keep the local version for all conflicted files. The remote changes are discarded for conflicting files only -- non-conflicting changes from the remote are still applied.

### `theirs`

Take the remote version for all conflicted files. Local changes are discarded for conflicting files.

### `interactive`

Presents a TUI prompt for each conflicted file, showing both versions. The user chooses which to keep or can edit manually. Only available via CLI, not MCP.

### `agent` (LLM-based)

The most sophisticated strategy. Instead of resolving immediately, it persists the conflict state and returns a report for the agent to handle.

## Agent conflict resolution

When `strategy=agent` is used, the flow becomes a multi-step process across MCP calls:

### Step 1: Pull with agent strategy

```
context_sync_pull(strategy="agent")
  --> Returns: {"status": "conflicts", "report": {...}}
  --> Persists: .context-teleport/.pending_conflicts.json (gitignored)
```

The `ConflictReport` contains:

- `conflict_id`: UUID for this merge operation
- `conflicts`: list of `ConflictEntry` objects, each with:
  - `file_path`: relative path
  - `ours_content`: local version
  - `theirs_content`: remote version
  - `base_content`: common ancestor
  - `resolved`: boolean
  - `resolution`: resolved content (when resolved)

### Step 2: Examine each conflict

```
context_conflict_detail(file_path="knowledge/architecture.md")
  --> Returns: {
        ours_content, theirs_content, base_content,
        diff (unified format),
        section_analysis (for .md files): {
          has_section_conflicts, conflict_details, auto_merged_content
        }
      }
```

For markdown files, the section analysis shows whether section-level merge can auto-resolve the conflict. If `has_section_conflicts` is `False`, the `auto_merged_content` can be used directly.

### Step 3: Resolve each file

```
context_resolve_conflict(
    file_path="knowledge/architecture.md",
    content="...merged content..."
)
  --> Updates the ConflictEntry, persists to disk
  --> Returns: {"status": "resolved", "remaining": N}
```

### Step 4: Finalize

```
context_merge_finalize()
  --> Applies all resolutions to working tree
  --> Falls back to 'ours' for any unresolved files
  --> Commits the merge
  --> Clears .pending_conflicts.json
```

### Abort

At any point, the agent can abort:

```
context_merge_abort()
  --> Clears .pending_conflicts.json
  --> Does not modify working tree
```

## Persistent conflict state

Conflict state is stored in `.context-teleport/.pending_conflicts.json`, which is gitignored. This is necessary because:

1. MCP tools are stateless -- each call is independent
2. The agent may need multiple turns to examine and resolve conflicts
3. The state must survive across tool invocations

The `ConflictReport` serializes to JSON via `to_json()`/`from_json()` methods, with UUIDs as `conflict_id` values for disk round-trips.

## Auto-push on shutdown

The MCP server's `_server_lifespan` context manager performs a best-effort push on shutdown:

```python
@asynccontextmanager
async def _server_lifespan(app):
    try:
        yield
    finally:
        try:
            gs = GitSync(store.root)
            if gs._has_changes():
                gs.push()
        except Exception:
            pass  # Best-effort, don't block shutdown
```

This catches the case where an agent made changes but forgot to push. The operation is silent on failure (e.g., no remote, auth issues, network down).
