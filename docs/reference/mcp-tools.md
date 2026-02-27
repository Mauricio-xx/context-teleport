# MCP Tools

Context Teleport exposes **27 MCP tools** that agents use to read and write project context. All tools return JSON strings. Agent identity is automatically detected via the `MCP_CALLER` environment variable (set during adapter registration).

Tools are organized into eight categories: [Knowledge Management](#knowledge-management), [Conventions](#conventions), [Skills](#skills), [Decisions](#decisions), [State and History](#state-and-history), [Scoping](#scoping), [Git Sync](#git-sync), and [Conflict Resolution](#conflict-resolution).

---

## Knowledge Management

### `context_search`

Search across all context files for a query string. Returns ranked results with file path, key, line number, matching text, and relevance score.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | *required* | The search query string |

**Returns:**

```json
[
  {
    "key": "architecture",
    "file": "knowledge/architecture.md",
    "line": 12,
    "text": "We use a microservices architecture with gRPC",
    "score": 0.95
  }
]
```

**Example:**

```
context_search(query="database migration")
```

---

### `context_add_knowledge`

Add or update a knowledge entry. If the key already exists, the content is overwritten. The calling agent is automatically recorded as the author.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | *required* | Identifier for the entry (e.g. `architecture`, `tech-stack`) |
| `content` | `str` | *required* | Markdown content for the entry |
| `scope` | `str` | `""` | Optional scope: `public`, `private`, or `ephemeral`. Empty means no scope change (defaults to `public` for new entries). |

**Returns:**

```json
{"status": "ok", "key": "architecture"}
```

**Example:**

```
context_add_knowledge(
    key="tech-stack",
    content="## Stack\n\n- Python 3.12\n- FastAPI\n- PostgreSQL 16",
    scope="public"
)
```

---

### `context_remove_knowledge`

Remove a knowledge entry by key.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | *required* | Identifier of the entry to remove |

**Returns:**

```json
{"status": "removed", "key": "tech-stack"}
```

Returns `{"status": "not_found", "key": "..."}` if the key does not exist.

---

### `context_get`

Read any value from the context store by dotpath. Supports traversal into knowledge, decisions, state, manifest, and other top-level sections.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dotpath` | `str` | *required* | Dot-separated path to the value |

**Dotpath examples:**

- `knowledge.architecture` -- content of a specific knowledge entry
- `decisions.1` -- decision with ID 1
- `state` -- full active state
- `manifest.project.name` -- project name from manifest

**Returns:**

The resolved value as JSON. Returns `{"error": "No value at '<dotpath>'"}` if the path does not resolve.

**Example:**

```
context_get(dotpath="manifest.project.name")
```

---

### `context_set`

Set a value by dotpath. Writes to the underlying store file.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dotpath` | `str` | *required* | Dot-separated path to the value |
| `value` | `str` | *required* | Value to set |

**Returns:**

```json
{"status": "ok", "dotpath": "state.current_task"}
```

Returns `{"status": "error", "error": "..."}` if the path is invalid.

**Example:**

```
context_set(dotpath="state.current_task", value="Implementing auth middleware")
```

---

## Conventions

Team conventions are shared behavioral rules (git workflow, environment constraints, communication style) that apply across all agents and tools.

### `context_add_convention`

Add or update a team convention. If the key already exists, the content is overwritten. The calling agent is automatically recorded as the author.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | *required* | Identifier for the convention (e.g. `git`, `environment`, `naming`) |
| `content` | `str` | *required* | Markdown content describing the convention |
| `scope` | `str` | `""` | Optional scope: `public`, `private`, or `ephemeral`. Empty means no change (defaults to `public` for new entries). |

**Returns:**

```json
{"status": "ok", "key": "git"}
```

**Example:**

```
context_add_convention(
    key="git",
    content="Always use feature branches.\nCommit early, commit often.\nNo force-push to main.",
    scope="public"
)
```

---

### `context_get_convention`

Read a specific convention by key.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | *required* | Identifier of the convention to read |

**Returns:**

```json
{"key": "git", "content": "Always use feature branches.\nCommit early, commit often.\nNo force-push to main."}
```

Returns `{"error": "Convention 'nonexistent' not found"}` if the key does not exist.

---

### `context_list_conventions`

List all team conventions with their keys and scopes.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| *(none)* | | | |

**Returns:**

```json
[
  {
    "key": "git",
    "content": "Always use feature branches...",
    "scope": "public"
  },
  {
    "key": "environment",
    "content": "No sudo. Use venvs...",
    "scope": "public"
  }
]
```

---

### `context_rm_convention`

Remove a team convention by key.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `key` | `str` | *required* | Identifier of the convention to remove |

**Returns:**

```json
{"status": "removed", "key": "git"}
```

Returns `{"status": "not_found", "key": "..."}` if the key does not exist.

---

## Skills

### `context_add_skill`

Add or update an agent skill. Constructs a `SKILL.md` file with YAML frontmatter from the provided name, description, and instructions. The calling agent is recorded automatically.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | *required* | Skill name (used as directory name, e.g. `deploy-staging`) |
| `description` | `str` | *required* | Short description of what the skill does |
| `instructions` | `str` | *required* | Markdown instructions for the skill body |
| `scope` | `str` | `""` | Optional scope: `public`, `private`, or `ephemeral` |

**Returns:**

```json
{"status": "ok", "name": "deploy-staging"}
```

**Example:**

```
context_add_skill(
    name="run-tests",
    description="Execute the full test suite with coverage",
    instructions="## Steps\n\n1. Activate venv\n2. Run `pytest tests/ -v --cov`\n3. Check coverage is above 80%",
    scope="public"
)
```

!!! note "SKILL.md format"
    The tool constructs the full SKILL.md automatically. You provide the parts; it assembles the YAML frontmatter (`name`, `description`) and appends the instructions as the markdown body.

---

### `context_remove_skill`

Remove an agent skill by name.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | *required* | Name of the skill to remove |

**Returns:**

```json
{"status": "removed", "name": "run-tests"}
```

Returns `{"status": "not_found", "name": "..."}` if the skill does not exist.

---

### `context_report_skill_usage`

Record that a skill was used in the current session. Appends a usage event to the skill's `.usage.ndjson` sidecar file for tracking adoption and frequency.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skill_name` | `str` | *required* | Name of the skill that was used |

**Returns:**

```json
{"status": "ok", "event_id": "a1b2c3d4-..."}
```

Returns `{"status": "error", "error": "..."}` if the skill does not exist.

---

### `context_rate_skill`

Rate a skill and optionally leave feedback. Appends to the skill's `.feedback.ndjson` sidecar file. Skills with an average rating below 3.0 and 2 or more ratings are automatically flagged as needing attention.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skill_name` | `str` | *required* | Name of the skill to rate |
| `rating` | `int` | *required* | Rating from 1 (poor) to 5 (excellent) |
| `comment` | `str` | `""` | Optional feedback comment |

**Returns:**

```json
{"status": "ok", "feedback_id": "e5f6g7h8-..."}
```

!!! info "Attention threshold"
    A skill is flagged `needs_attention = true` when it has 2 or more ratings and the average drops below 3.0. Flagged skills appear in the MCP server instructions and in `context-teleport skill review`.

---

### `context_propose_skill_improvement`

Create an improvement proposal for an existing skill. The proposal includes the full new SKILL.md content and a computed diff summary (via `difflib`). Proposals can be reviewed and resolved via CLI (`context-teleport skill apply-proposal`) or programmatically.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skill_name` | `str` | *required* | Name of the skill to improve |
| `proposed_content` | `str` | *required* | Full new SKILL.md content (frontmatter + body) |
| `rationale` | `str` | `""` | Why this improvement is needed |

**Returns:**

```json
{
  "status": "ok",
  "proposal_id": "i9j0k1l2-...",
  "diff_summary": "@@ -3,5 +3,7 @@\n ..."
}
```

---

### `context_list_skill_proposals`

List skill improvement proposals with optional filters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skill_name` | `str` | `""` | Filter by skill name. Empty for all skills. |
| `status` | `str` | `""` | Filter by status: `pending`, `accepted`, `rejected`, `upstream`. Empty for all. |

**Returns:**

```json
[
  {
    "id": "i9j0k1l2-...",
    "skill_name": "deploy-staging",
    "agent": "claude-code",
    "status": "pending",
    "diff_summary": "@@ -3,5 +3,7 @@ ...",
    "rationale": "Add rollback step for failed deployments...",
    "created_at": "2025-05-10T14:30:00+00:00"
  }
]
```

!!! note "Rationale truncation"
    The `rationale` field in list results is truncated to 100 characters. Use `context://skills/{name}/proposals` resource for full content.

---

## Decisions

### `context_record_decision`

Record an architectural decision in ADR (Architecture Decision Record) style. Decisions are auto-assigned sequential IDs.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | `str` | *required* | Short decision title |
| `context` | `str` | `""` | Why this decision was needed |
| `decision` | `str` | `""` | What was decided |
| `consequences` | `str` | `""` | Expected impact |
| `scope` | `str` | `""` | Optional scope: `public`, `private`, or `ephemeral`. Defaults to `public`. |

**Returns:**

```json
{"status": "ok", "id": 3, "title": "Use PostgreSQL for persistence"}
```

**Example:**

```
context_record_decision(
    title="Use PostgreSQL for persistence",
    context="Need ACID transactions and JSON support",
    decision="PostgreSQL 16 with pgvector extension",
    consequences="Team needs PostgreSQL expertise. Adds infra complexity."
)
```

---

## State and History

### `context_update_state`

Update the active session state. Partial updates are supported -- only provided fields are changed.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `current_task` | `str` | `""` | What you are currently working on. Empty means no change. |
| `blockers` | `str` | `""` | Comma-separated list of blockers. Empty string clears all blockers. |

**Returns:**

```json
{"status": "ok", "current_task": "Implementing auth middleware"}
```

**Example:**

```
context_update_state(
    current_task="Implementing auth middleware",
    blockers="Waiting for API spec, Redis not configured"
)
```

---

### `context_append_session`

Append a session summary to the history log. Each summary gets a unique UUID.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent` | `str` | `""` | Agent identifier (e.g. `claude-code`, `cursor`) |
| `summary` | `str` | `""` | Brief summary of what was done |
| `knowledge_added` | `str` | `""` | Comma-separated list of knowledge keys added |
| `decisions_added` | `str` | `""` | Comma-separated list of decision IDs added |

**Returns:**

```json
{"status": "ok", "session_id": "m3n4o5p6-..."}
```

**Example:**

```
context_append_session(
    agent="claude-code",
    summary="Set up database schema and migrations",
    knowledge_added="tech-stack, db-schema",
    decisions_added="3"
)
```

---

## Scoping

### `context_get_scope`

Get the current visibility scope of a knowledge entry, decision, convention, or skill.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_type` | `str` | *required* | Either `knowledge`, `decision`, `convention`, or `skill` |
| `key` | `str` | *required* | The entry key (knowledge key, decision ID/title, convention key, or skill name) |

**Returns:**

```json
{"key": "architecture", "scope": "public"}
```

---

### `context_set_scope`

Change the visibility scope of a knowledge entry, decision, convention, or skill.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_type` | `str` | *required* | Either `knowledge`, `decision`, `convention`, or `skill` |
| `key` | `str` | *required* | The entry key |
| `scope` | `str` | *required* | New scope: `public`, `private`, or `ephemeral` |

**Returns:**

```json
{"status": "ok", "key": "architecture", "scope": "private"}
```

!!! info "Scope behavior"
    - **public** (default): Included in sync, export, and onboarding.
    - **private**: Not synced (excluded from git staging). Excluded from adapter export and onboarding prompts.
    - **ephemeral**: Not synced. Local-only. Excluded from everything except direct reads.

---

## Git Sync

### `context_sync_push`

Commit and push context changes to the git remote. If no remote is configured, performs a local commit only.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `message` | `str` | `""` | Optional commit message. Auto-generated from changed files if empty. |

**Returns:**

```json
{"status": "pushed", "commit": "a1b2c3d"}
```

Or, if no remote is configured:

```json
{"status": "committed", "commit": "a1b2c3d"}
```

!!! note "Auto-push on shutdown"
    The MCP server performs a best-effort push during its lifespan shutdown. Explicit `context_sync_push` calls are still recommended before ending a session.

---

### `context_sync_pull`

Pull context changes from the git remote and merge. Supports three conflict resolution strategies.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `strategy` | `str` | `"ours"` | Conflict resolution strategy: `ours`, `theirs`, or `agent` |

**Strategy options:**

| Strategy | Behavior |
|----------|----------|
| `ours` | Keep local version on conflict. Silent, no agent interaction. |
| `theirs` | Keep remote version on conflict. Silent, no agent interaction. |
| `agent` | Detect conflicts, persist state, and return a conflict report. The agent then uses `context_conflict_detail`, `context_resolve_conflict`, and `context_merge_finalize` to resolve interactively. |

**Returns (clean pull):**

```json
{"status": "pulled", "commit": "d4e5f6g"}
```

**Returns (conflicts with `agent` strategy):**

```json
{
  "status": "conflicts",
  "conflict_id": "h7i8j9k0-...",
  "files": [".context-teleport/knowledge/architecture.md"]
}
```

!!! tip "Section-level merge"
    For markdown files, Context Teleport attempts section-level merge (by `## ` headers) before falling back to the chosen strategy. Changes in different sections are auto-resolved even when git reports a conflict.

---

## Conflict Resolution

These five tools work together for interactive conflict resolution when using `context_sync_pull(strategy="agent")`.

### `context_merge_status`

Check if there are unresolved merge conflicts. Reads from the disk-persisted conflict state at `.context-teleport/.pending_conflicts.json`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| *(none)* | | | |

**Returns (clean):**

```json
{"status": "clean"}
```

**Returns (conflicts pending):**

```json
{
  "status": "conflicts",
  "conflict_id": "h7i8j9k0-...",
  "report": {
    "conflicts": [...],
    "auto_resolved": [...]
  }
}
```

---

### `context_conflict_detail`

Get detailed conflict information for a single file. Returns the full content from all three sides (ours, theirs, base), a unified diff, and section-level analysis for markdown files.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | `str` | *required* | Path of the conflicted file (relative to project root) |

**Returns:**

```json
{
  "file_path": ".context-teleport/knowledge/architecture.md",
  "ours_content": "...",
  "theirs_content": "...",
  "base_content": "...",
  "diff": "--- .../architecture.md (ours)\n+++ .../architecture.md (theirs)\n...",
  "section_analysis": {
    "has_section_conflicts": false,
    "conflict_details": [],
    "auto_merged_content": "..."
  }
}
```

!!! tip "Auto-merge hint"
    When `section_analysis.has_section_conflicts` is `false` and `auto_merged_content` is non-null, you can pass that content directly to `context_resolve_conflict` without manual merging.

---

### `context_resolve_conflict`

Resolve a single merge conflict by providing the final content. The resolution is persisted to disk. Call `context_merge_finalize` when all conflicts are resolved.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | `str` | *required* | Path of the conflicted file (relative to project root) |
| `content` | `str` | *required* | Final resolved content for the file |

**Returns:**

```json
{
  "status": "resolved",
  "file_path": ".context-teleport/knowledge/architecture.md",
  "remaining": 0
}
```

---

### `context_merge_finalize`

Finalize the merge after resolving conflicts. Applies resolved content to files, falls back to `ours` for any still-unresolved files, and commits the merge. Clears the pending conflict state.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| *(none)* | | | |

**Returns:**

```json
{"status": "merged", "commit": "l1m2n3o4"}
```

---

### `context_merge_abort`

Abort the pending merge and discard conflict state. The pending conflicts file is removed. The next `context_sync_pull` will re-detect conflicts.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| *(none)* | | | |

**Returns:**

```json
{"status": "aborted"}
```

---

## Error Handling

All tools follow a consistent error pattern. When an operation fails, the returned JSON includes a `status` field set to `"error"` and an `error` field with a human-readable message:

```json
{"status": "error", "error": "Knowledge entry 'nonexistent' not found"}
```

Common error conditions:

| Condition | Behavior |
|-----------|----------|
| Store not initialized | `RuntimeError: Not inside a project with a context store or git repo` |
| Invalid scope string | `{"error": "Invalid scope '...' . Use public, private, or ephemeral."}` |
| Invalid strategy string | `{"status": "error", "error": "Invalid strategy '...' . Use: ours, theirs, agent."}` |
| Entry not found | `{"status": "not_found", ...}` or `{"error": "... not found"}` |
| Git operation fails | `{"status": "error", "error": "<GitSyncError message>"}` |

---

## Agent Identity

The MCP server detects the calling agent via the `MCP_CALLER` environment variable. When an adapter registers Context Teleport as an MCP server, it sets this variable in the MCP configuration's `env` block. If `MCP_CALLER` is not set, the agent name defaults to `mcp:unknown`.

Agent identity is recorded on:

- Knowledge entries (`author` field)
- Decision records (`author` field)
- Skill entries (`agent` field)
- Session summaries (`agent` field)
- Usage events and feedback (`agent` field)
- Skill proposals (`agent` field)
