# Bundle Format

The `.context-teleport/` directory is the on-disk representation of the context store. It lives at the root of your project alongside your source code.

## Directory layout

```
.context-teleport/
  manifest.json                      # Project metadata and schema version
  .gitignore                         # Auto-generated: excludes private/ephemeral + local state
  knowledge/
    *.md                             # Knowledge entries (one file per key)
    .scope.json                      # Scope sidecar: maps filenames to private/ephemeral
    .meta.json                       # Author metadata per entry
    decisions/
      0001-decision-title.md         # ADR-style decision records
      .scope.json                    # Decision scope sidecar
  skills/
    <name>/
      SKILL.md                       # Agent skill (YAML frontmatter + markdown body)
      .usage.ndjson                  # Append-only usage events (created lazily)
      .feedback.ndjson               # Append-only feedback entries (created lazily)
      .proposals/
        <uuid>.json                  # Improvement proposals
    .scope.json                      # Skill scope sidecar
  state/
    active.json                      # Current task, blockers, progress (gitignored)
    roadmap.json                     # Project roadmap
  preferences/
    team.json                        # Team preferences (synced via git)
    user.json                        # User preferences (gitignored)
  history/
    sessions.ndjson                  # Append-only session log
```

## File descriptions

### manifest.json

The root configuration file. Created by `context-teleport init`.

```json
{
  "schema_version": "0.4.0",
  "project": {
    "name": "my-project",
    "id": "a1b2c3d4-...",
    "repo_url": "git@github.com:team/my-project.git"
  },
  "adapters": {
    "claude_code": { "enabled": true }
  },
  "team": { "members": [] },
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

### Knowledge entries (`knowledge/*.md`)

Plain markdown files, one per key. The filename is the key (e.g., `architecture.md` for key `architecture`).

```markdown
We use hexagonal architecture with FastAPI.

## Layers
- Domain: pure Python, no framework deps
- Ports: abstract interfaces
- Adapters: FastAPI routes, SQLAlchemy repos
```

### Scope sidecars (`.scope.json`)

JSON files that map filenames to non-default scopes. Only entries with `private` or `ephemeral` scope appear here -- `public` is the default and is not stored.

```json
{
  "local-notes.md": "private",
  "scratch.md": "ephemeral"
}
```

### Author metadata (`.meta.json`)

Tracks which agent wrote each entry.

```json
{
  "architecture.md": {
    "author": "mcp:claude-code",
    "updated_at": "2025-01-15T10:30:00Z"
  }
}
```

### Decision records (`knowledge/decisions/*.md`)

ADR-format markdown files with sequential numbering.

```markdown
# 0001 - Use PostgreSQL over SQLite

**Date**: 2025-01-15
**Status**: accepted
**Author**: mcp:claude-code

## Context
We need a database that supports concurrent writes from multiple services.

## Decision
Use PostgreSQL for all persistent storage.

## Consequences
Requires running a PostgreSQL server in development. Docker Compose handles this.
```

### SKILL.md files (`skills/<name>/SKILL.md`)

YAML frontmatter followed by markdown instructions.

```markdown
---
name: deploy-staging
description: Deploy the application to the staging environment
---

## Steps

1. Run the test suite: `pytest tests/ -v`
2. Build the Docker image: `docker build -t app:staging .`
3. Push to registry: `docker push registry.example.com/app:staging`
4. Deploy: `kubectl apply -f k8s/staging/`

## Verification

Check the staging URL responds with 200.
```

### Skill tracking files

These are created lazily when skills are used or rated.

**`.usage.ndjson`** -- one JSON object per line:

```json
{"id": "uuid", "session_id": "", "agent": "mcp:claude-code", "timestamp": "2025-01-15T10:00:00Z"}
```

**`.feedback.ndjson`** -- one JSON object per line:

```json
{"id": "uuid", "agent": "mcp:cursor", "rating": 4, "comment": "Clear steps", "timestamp": "2025-01-15T11:00:00Z"}
```

**`.proposals/<uuid>.json`** -- full proposal object:

```json
{
  "id": "uuid",
  "skill_name": "deploy-staging",
  "agent": "mcp:claude-code",
  "rationale": "Add rollback step",
  "proposed_content": "---\nname: deploy-staging\n...",
  "diff_summary": "--- old\n+++ new\n...",
  "status": "pending",
  "created_at": "2025-01-15T12:00:00Z"
}
```

### State files

**`state/active.json`** -- gitignored, session-local:

```json
{
  "current_task": "Implement user authentication",
  "blockers": ["waiting on API key"],
  "progress": {},
  "last_agent": "mcp:claude-code",
  "updated_at": "2025-01-15T10:00:00Z"
}
```

**`state/roadmap.json`** -- synced:

```json
{
  "items": [
    {"title": "MVP release", "status": "in-progress", "milestone": "v1.0"}
  ]
}
```

### Session history (`history/sessions.ndjson`)

Append-only NDJSON log of session summaries:

```json
{"id": "uuid", "agent": "claude-code", "summary": "Added auth knowledge and DB decision", "knowledge_added": ["auth"], "decisions_added": ["1"], "skills_used": ["deploy-staging"], "started": "2025-01-15T10:00:00Z"}
```

### Preferences

**`preferences/team.json`** -- synced, shared settings:

```json
{
  "values": {
    "default_scope": "public",
    "default_strategy": "ours"
  }
}
```

**`preferences/user.json`** -- gitignored, personal settings:

```json
{
  "values": {
    "editor": "vim"
  }
}
```

## Sync behavior

| Path | Git-synced | Notes |
|------|-----------|-------|
| `manifest.json` | Yes | Always synced |
| `knowledge/*.md` | Scope-dependent | Public: synced. Private/ephemeral: gitignored |
| `knowledge/.scope.json` | Yes | Scope metadata always synced |
| `knowledge/.meta.json` | Yes | Author metadata always synced |
| `knowledge/decisions/*.md` | Scope-dependent | Same rules as knowledge |
| `skills/*/SKILL.md` | Scope-dependent | Same rules as knowledge |
| `skills/*/.usage.ndjson` | Yes | Tracking data synced |
| `skills/*/.feedback.ndjson` | Yes | Feedback synced |
| `skills/*/.proposals/*.json` | Yes | Proposals synced |
| `state/active.json` | No | Session-local, gitignored |
| `state/roadmap.json` | Yes | Team roadmap synced |
| `preferences/team.json` | Yes | Shared preferences |
| `preferences/user.json` | No | Personal, gitignored |
| `history/sessions.ndjson` | Yes | Session log synced |

## Auto-generated .gitignore

The store's `.gitignore` is created by `context-teleport init` and updated as scopes change:

```gitignore
# Context Teleport auto-generated
state/active.json
preferences/user.json
.pending_conflicts.json
```

Private and ephemeral files are added dynamically when their scope is set.
