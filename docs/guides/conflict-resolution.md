# Conflict Resolution

This guide is a deep dive into how Context Teleport handles merge conflicts when
multiple developers or agents push concurrent changes to the same context store.

## How merge works

Context Teleport stores knowledge as individual markdown files under
`.context-teleport/knowledge/`. When you run `context-teleport pull` (or an agent
calls `context_sync_pull`), it fetches remote changes and attempts to merge them.

The merge system works in two layers:

1. **Git-level merge** -- standard git merge for file-level changes (new files, deleted
   files, changes to different files).
2. **Section-level merge** -- for markdown files that both sides modified, Context
   Teleport splits the file by `## ` headers and performs a 3-way merge at the section
   granularity.

## Section-level merge

Markdown files are split into sections at `## ` header boundaries. Each section is
treated as an independent unit for merging.

**Example:** Two developers edit the same knowledge entry.

Base version:

```markdown
## Architecture
REST API with FastAPI.

## Database
PostgreSQL with connection pooling.

## Deployment
Docker containers on Kubernetes.
```

Person A modifies the Architecture section:

```markdown
## Architecture
REST API with FastAPI. Added GraphQL gateway for mobile clients.
```

Person B modifies the Deployment section:

```markdown
## Deployment
Docker containers on Kubernetes. Migrated to Helm charts.
```

Because the changes are in different sections, Context Teleport merges them
automatically without conflict. The result contains both changes.

### When section-level merge fails

If both sides modify the *same* section, the section merge cannot auto-resolve and
a conflict is reported. This is the only case where manual intervention is needed.

## Merge strategies

Context Teleport supports four conflict resolution strategies:

| Strategy      | Behavior                                                | Use case                     |
|---------------|---------------------------------------------------------|------------------------------|
| `ours`        | Keep local version for conflicted files                 | Default, safe, no data loss  |
| `theirs`      | Take remote version for conflicted files                | When remote is authoritative |
| `interactive` | TUI prompt for each conflict (CLI only)                 | Human review in terminal     |
| `agent`       | Expose conflicts to the AI agent for resolution via MCP | Agent-driven workflows       |

### Ours (default)

```bash
context-teleport pull --strategy ours
```

Keeps your local version for any conflicted files. Non-conflicted changes from the
remote are still applied normally. This is the default strategy because it never
discards your local work.

### Theirs

```bash
context-teleport pull --strategy theirs
```

Takes the remote version for conflicted files. Use this when you know the remote
version is correct and your local changes should be discarded.

### Interactive

```bash
context-teleport pull --strategy interactive
```

Opens a terminal UI for each conflicted file, showing the diff and letting you choose
between ours, theirs, or a manually edited resolution. Only works in interactive
terminals (not piped output).

### Agent

The `agent` strategy is designed for MCP-connected AI agents. Instead of resolving
conflicts immediately, it exposes them through a multi-step MCP tool process.

## Agent resolution flow

When an agent encounters conflicts, the resolution happens in four steps. Conflict
state is persisted to `.context-teleport/.pending_conflicts.json` (gitignored), so it
survives across separate MCP tool calls.

### Step 1: Pull with agent strategy

```
Agent: [calls context_sync_pull(strategy="agent")]

Response:
{
  "status": "conflicts",
  "report": {
    "conflict_id": "a1b2c3d4-...",
    "conflicts": [
      {
        "file_path": ".context-teleport/knowledge/api-design.md",
        "resolved": false
      }
    ],
    "unresolved": 1
  }
}
```

The conflict report is saved to disk. The agent now knows which files have conflicts.

### Step 2: Inspect each conflict

```
Agent: [calls context_conflict_detail(
         file_path=".context-teleport/knowledge/api-design.md"
       )]

Response:
{
  "file_path": ".context-teleport/knowledge/api-design.md",
  "ours_content": "## API Design\nREST with snake_case...",
  "theirs_content": "## API Design\nREST with camelCase...",
  "base_content": "## API Design\nREST API...",
  "diff": "--- ours\n+++ theirs\n@@ ...",
  "section_analysis": {
    "has_section_conflicts": true,
    "conflict_details": ["Section 'API Design': both sides modified"],
    "auto_merged_content": null
  }
}
```

The agent receives the full content from all three sides (base, ours, theirs), a
unified diff, and -- for markdown files -- a section-level analysis showing exactly
which sections conflict.

### Step 3: Resolve each file

The agent crafts the final content, combining the best of both versions:

```
Agent: [calls context_resolve_conflict(
         file_path=".context-teleport/knowledge/api-design.md",
         content="## API Design\nREST API with snake_case for external endpoints.\ncamelCase permitted for internal service-to-service calls.\n"
       )]

Response:
{
  "status": "resolved",
  "file_path": ".context-teleport/knowledge/api-design.md",
  "remaining": 0
}
```

Repeat for each conflicted file. The resolution is persisted to disk after each call.

### Step 4: Finalize the merge

Once all (or some) conflicts are resolved:

```
Agent: [calls context_merge_finalize()]

Response:
{
  "status": "merged",
  "resolved": 1,
  "skipped": 0
}
```

This applies the resolved content to the working tree, falls back to `ours` for any
files that were not explicitly resolved, and commits the merge.

### Aborting

If the agent decides not to proceed:

```
Agent: [calls context_merge_abort()]

Response:
{
  "status": "aborted"
}
```

This clears the pending conflict state without merging. The next pull will re-detect
the conflicts.

## Persistent conflict state

The conflict state file (`.pending_conflicts.json`) is stored in the
`.context-teleport/` directory and is gitignored. This is intentional:

- It survives across separate MCP tool calls (each MCP tool invocation is stateless).
- It does not pollute the git history.
- It is cleaned up by `context_merge_finalize()` or `context_merge_abort()`.

You can check the current conflict state at any time:

```
Agent: [calls context_merge_status()]

Response:
{
  "status": "conflicts",
  "conflict_id": "a1b2c3d4-...",
  "report": { ... }
}
```

Or from the CLI:

```bash
context-teleport sync resolve --strategy ours
```

## Best practices for avoiding conflicts

1. **Use small, focused knowledge entries.** A single entry per topic means two
   developers are unlikely to edit the same file. Prefer `api-auth`, `api-pagination`,
   `api-versioning` over one large `api-design` entry.

2. **Skills rarely conflict.** Each skill is its own directory with its own `SKILL.md`.
   Two developers editing different skills never conflict. Even within a skill, the
   sidecar files (`.usage.ndjson`, `.feedback.ndjson`) are append-only and merge
   cleanly.

3. **Decisions are append-only.** Architecture Decision Records (ADRs) are never
   modified after creation, only new ones are added. This eliminates conflicts on
   decision files entirely.

4. **NDJSON files merge naturally.** Session logs, usage events, and feedback entries
   are stored as newline-delimited JSON. Because each entry is a separate line, git
   can merge concurrent appends without conflict in most cases.

5. **Pull before pushing.** The simplest way to avoid conflicts is to pull the latest
   remote state before starting a session. The MCP server does not auto-pull on
   startup, so either pull via CLI or have the agent do it at the start of a session.

## CLI reference

```bash
# Pull with explicit strategy
context-teleport pull --strategy ours|theirs|interactive

# Resolve pending conflicts
context-teleport sync resolve --strategy ours|theirs

# Check for changes before pulling
context-teleport diff --remote

# View sync history
context-teleport log --oneline -n 20
```
