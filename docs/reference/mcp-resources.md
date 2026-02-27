# MCP Resources

Context Teleport exposes **15 MCP resources** that provide read-only access to the context store. Resources follow the `context://` URI scheme and return JSON strings.

Resources are organized into six groups: [Project Metadata](#project-metadata), [Knowledge](#knowledge), [Conventions](#conventions), [Decisions](#decisions), [State and History](#state-and-history), and [Skills](#skills).

---

## Project Metadata

### `context://manifest`

Project metadata and configuration. Returns the full `Manifest` model as JSON.

**URI:** `context://manifest`

**Response schema:**

```json
{
  "schema_version": "0.4.0",
  "project": {
    "name": "my-project",
    "id": "a1b2c3d4-...",
    "repo_url": "https://github.com/org/my-project"
  },
  "adapters": {
    "claude_code": {"enabled": true}
  },
  "team": {
    "members": [
      {"name": "alice", "machine": "laptop", "added": "2025-05-01T10:00:00Z"}
    ]
  },
  "created_at": "2025-05-01T10:00:00Z",
  "updated_at": "2025-05-10T14:30:00Z"
}
```

### `context://summary`

High-level project context summary. Returns an aggregated overview computed from the store state, including counts and key lists.

**URI:** `context://summary`

**Response schema:**

```json
{
  "project": "my-project",
  "knowledge_count": 12,
  "convention_count": 3,
  "decisions_count": 5,
  "skills_count": 3,
  "current_task": "Implementing auth middleware",
  "blockers": ["Waiting for API spec"]
}
```

---

## Knowledge

### `context://knowledge`

List all knowledge entries with their keys, content, and scopes.

**URI:** `context://knowledge`

**Response schema:**

```json
[
  {
    "key": "architecture",
    "content": "## Architecture\n\nMicroservices with gRPC...",
    "scope": "public"
  },
  {
    "key": "credentials-setup",
    "content": "...",
    "scope": "private"
  }
]
```

!!! note
    All entries are returned regardless of scope. Scope filtering happens at the adapter export and onboarding prompt level, not at the resource level.

### `context://knowledge/{key}`

Read a single knowledge entry by key. Returns the key and full markdown content.

**URI:** `context://knowledge/{key}`

**URI parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Knowledge entry identifier |

**Response schema:**

```json
{
  "key": "architecture",
  "content": "## Architecture\n\nMicroservices with gRPC..."
}
```

**Error response:**

```json
{"error": "Knowledge entry 'nonexistent' not found"}
```

---

## Conventions

### `context://conventions`

List all team conventions with their keys, content, and scopes.

**URI:** `context://conventions`

**Response schema:**

```json
[
  {
    "key": "git",
    "content": "Always use feature branches.\nCommit early, commit often.",
    "scope": "public"
  },
  {
    "key": "environment",
    "content": "No sudo. Use venvs. Docker when needed.",
    "scope": "public"
  }
]
```

### `context://conventions/{key}`

Read a single convention by key. Returns the key and full markdown content.

**URI:** `context://conventions/{key}`

**URI parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `key` | `str` | Convention identifier |

**Response schema:**

```json
{
  "key": "git",
  "content": "Always use feature branches.\nCommit early, commit often."
}
```

**Error response:**

```json
{"error": "Convention 'nonexistent' not found"}
```

---

## Decisions

### `context://decisions`

List all architectural decisions with their IDs, titles, statuses, and scopes.

**URI:** `context://decisions`

**Response schema:**

```json
[
  {
    "id": 1,
    "title": "Use PostgreSQL for persistence",
    "status": "accepted",
    "scope": "public"
  },
  {
    "id": 2,
    "title": "Adopt gRPC for service communication",
    "status": "proposed",
    "scope": "public"
  }
]
```

**Status values:** `proposed`, `accepted`, `deprecated`, `superseded`

### `context://decisions/{id}`

Read a single decision by ID or title. Returns the full ADR content.

**URI:** `context://decisions/{id}`

**URI parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `id` | `str` | Decision ID (numeric) or title |

**Response schema:**

```json
{
  "id": 1,
  "title": "Use PostgreSQL for persistence",
  "status": "accepted",
  "context": "Need ACID transactions and JSON support",
  "decision": "PostgreSQL 16 with pgvector extension",
  "consequences": "Team needs PostgreSQL expertise"
}
```

**Error response:**

```json
{"error": "Decision '99' not found"}
```

---

## State and History

### `context://state`

Current active session state. Returns the `ActiveState` model as JSON.

**URI:** `context://state`

**Response schema:**

```json
{
  "current_task": "Implementing auth middleware",
  "blockers": ["Waiting for API spec"],
  "progress": {"auth": "50%", "tests": "done"},
  "last_agent": "claude-code",
  "last_machine": "laptop",
  "updated_at": "2025-05-10T14:30:00Z"
}
```

### `context://history`

Recent session history. Returns a list of `SessionSummary` objects ordered by start time.

**URI:** `context://history`

**Response schema:**

```json
[
  {
    "id": "a1b2c3d4-...",
    "agent": "claude-code",
    "user": "",
    "machine": "",
    "started": "2025-05-10T14:00:00Z",
    "ended": null,
    "summary": "Set up database schema and migrations",
    "knowledge_added": ["tech-stack", "db-schema"],
    "decisions_added": ["3"],
    "skills_used": ["run-tests"]
  }
]
```

---

## Skills

### `context://skills`

List all agent skills with their names, descriptions, and scopes.

**URI:** `context://skills`

**Response schema:**

```json
[
  {
    "name": "deploy-staging",
    "description": "Deploy the application to staging environment",
    "scope": "public"
  },
  {
    "name": "run-tests",
    "description": "Execute the full test suite with coverage",
    "scope": "public"
  }
]
```

### `context://skills/{name}`

Read the full SKILL.md content for a specific skill, including YAML frontmatter and the markdown body.

**URI:** `context://skills/{name}`

**URI parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Skill name |

**Response schema:**

```json
{
  "name": "deploy-staging",
  "description": "Deploy the application to staging environment",
  "content": "---\nname: deploy-staging\ndescription: Deploy the application to staging environment\n---\n\n## Steps\n\n1. Build the Docker image\n2. Push to registry\n3. Update Kubernetes deployment"
}
```

**Error response:**

```json
{"error": "Skill 'nonexistent' not found"}
```

### `context://skills/stats`

Aggregated usage and feedback statistics for all skills. Returns computed `SkillStats` objects.

**URI:** `context://skills/stats`

**Response schema:**

```json
[
  {
    "skill_name": "deploy-staging",
    "usage_count": 15,
    "avg_rating": 4.2,
    "rating_count": 5,
    "last_used": "2025-05-10T14:30:00Z",
    "needs_attention": false
  },
  {
    "skill_name": "run-tests",
    "usage_count": 42,
    "avg_rating": 2.5,
    "rating_count": 4,
    "last_used": "2025-05-10T12:00:00Z",
    "needs_attention": true
  }
]
```

!!! info "Attention flag"
    `needs_attention` is `true` when a skill has 2 or more ratings and the average rating is below 3.0.

### `context://skills/{name}/feedback`

All feedback entries for a specific skill. Returns the raw `SkillFeedback` records from the `.feedback.ndjson` sidecar file.

**URI:** `context://skills/{name}/feedback`

**URI parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Skill name |

**Response schema:**

```json
[
  {
    "id": "e5f6g7h8-...",
    "agent": "claude-code",
    "rating": 4,
    "comment": "Clear instructions, easy to follow",
    "timestamp": "2025-05-10T14:30:00Z"
  },
  {
    "id": "i9j0k1l2-...",
    "agent": "cursor",
    "rating": 2,
    "comment": "Missing rollback step",
    "timestamp": "2025-05-09T10:00:00Z"
  }
]
```

**Error response:**

```json
{"error": "Skill 'nonexistent' not found"}
```

### `context://skills/{name}/proposals`

All improvement proposals for a specific skill. Returns `SkillProposal` records from the `.proposals/` sidecar directory.

**URI:** `context://skills/{name}/proposals`

**URI parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Skill name |

**Response schema:**

```json
[
  {
    "id": "m3n4o5p6-...",
    "skill_name": "deploy-staging",
    "agent": "claude-code",
    "rationale": "Add rollback step for failed deployments",
    "proposed_content": "---\nname: deploy-staging\n...",
    "diff_summary": "@@ -10,3 +10,7 @@\n ...",
    "status": "pending",
    "created_at": "2025-05-10T14:30:00Z",
    "resolved_at": null,
    "resolved_by": ""
  }
]
```

**Proposal status values:** `pending`, `accepted`, `rejected`, `upstream`

**Error response:**

```json
{"error": "Skill 'nonexistent' not found"}
```

---

## Resource Access Patterns

Resources are designed for two primary use cases:

1. **Onboarding** -- An agent reads `context://summary`, `context://conventions`, `context://knowledge`, `context://decisions`, and `context://skills` to understand the project state before starting work. The `context_onboarding` prompt automates this.

2. **Targeted lookup** -- An agent reads a specific entry (`context://knowledge/{key}`, `context://conventions/{key}`, `context://decisions/{id}`, `context://skills/{name}`) when it needs detailed content about a particular topic.

!!! warning "Resources are read-only"
    Resources provide read access only. To modify context, use the corresponding [MCP tools](mcp-tools.md). For example, read via `context://knowledge/{key}` and write via `context_add_knowledge()`.
