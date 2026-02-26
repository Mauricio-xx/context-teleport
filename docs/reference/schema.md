# Schema

All data models are defined as Pydantic v2 `BaseModel` subclasses in
`src/ctx/core/schema.py`. The current schema version is **0.4.0**, stored in
`ctx.core.migrations.SCHEMA_VERSION`.

---

## Manifest Layer

The manifest is the root configuration object for a context store, persisted as
`.context-teleport/manifest.json`.

### Manifest

```python
class Manifest(BaseModel):
    schema_version: str = SCHEMA_VERSION
    project: ProjectInfo
    adapters: dict[str, AdapterConfig] = {"claude_code": AdapterConfig(enabled=True)}
    team: dict[str, list[TeamMember]] = {"members": []}
    created_at: datetime
    updated_at: datetime
```

| Field | Type | Default | Description |
|---|---|---|---|
| `schema_version` | `str` | `"0.4.0"` | Schema version for migration support |
| `project` | `ProjectInfo` | required | Project identification |
| `adapters` | `dict[str, AdapterConfig]` | `{"claude_code": ...}` | Registered adapter configurations |
| `team` | `dict[str, list[TeamMember]]` | `{"members": []}` | Team member registry |
| `created_at` | `datetime` | now (UTC) | Store creation timestamp |
| `updated_at` | `datetime` | now (UTC) | Last modification timestamp |

### ProjectInfo

```python
class ProjectInfo(BaseModel):
    name: str
    id: str = Field(default_factory=uuid4)
    repo_url: str = ""
```

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Human-readable project name |
| `id` | `str` | UUID v4 | Unique project identifier |
| `repo_url` | `str` | `""` | Git remote URL |

### AdapterConfig

```python
class AdapterConfig(BaseModel):
    enabled: bool = True
```

| Field | Type | Default | Description |
|---|---|---|---|
| `enabled` | `bool` | `True` | Whether the adapter is active |

### TeamMember

```python
class TeamMember(BaseModel):
    name: str
    machine: str
    added: datetime = Field(default_factory=now)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Team member name |
| `machine` | `str` | required | Machine hostname |
| `added` | `datetime` | now (UTC) | When the member was registered |

---

## Knowledge

Knowledge entries are stored as markdown files under `.context-teleport/knowledge/`.
Each file corresponds to one `KnowledgeEntry`.

### KnowledgeEntry

```python
class KnowledgeEntry(BaseModel):
    key: str
    content: str
    updated_at: datetime = Field(default_factory=now)
    author: str = ""
    agent: str = ""
```

| Field | Type | Default | Description |
|---|---|---|---|
| `key` | `str` | required | Entry identifier (becomes filename: `<key>.md`) |
| `content` | `str` | required | Markdown content |
| `updated_at` | `datetime` | now (UTC) | Last update timestamp |
| `author` | `str` | `""` | Human author name |
| `agent` | `str` | `""` | Agent that wrote the entry (v0.3.0+) |

---

## Skills

Skills are stored as directories under `.context-teleport/skills/<name>/SKILL.md`.
Each SKILL.md file contains YAML frontmatter and a markdown body.

### SkillEntry

```python
class SkillEntry(BaseModel):
    name: str
    description: str
    content: str  # complete SKILL.md (frontmatter + body)
    updated_at: datetime = Field(default_factory=now)
    agent: str = ""
```

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | required | Skill name (directory name) |
| `description` | `str` | required | Short description (from frontmatter) |
| `content` | `str` | required | Full SKILL.md content including YAML frontmatter |
| `updated_at` | `datetime` | now (UTC) | Last update timestamp |
| `agent` | `str` | `""` | Agent that wrote the skill |

---

## Decisions (ADR)

Decision records follow the Architecture Decision Record pattern. Stored as numbered
markdown files under `.context-teleport/knowledge/decisions/`.

### DecisionStatus

```python
class DecisionStatus(str, Enum):
    proposed = "proposed"
    accepted = "accepted"
    deprecated = "deprecated"
    superseded = "superseded"
```

### Decision

```python
class Decision(BaseModel):
    id: int
    title: str
    status: DecisionStatus = DecisionStatus.accepted
    date: datetime = Field(default_factory=now)
    author: str = ""
    context: str = ""
    decision: str = ""
    consequences: str = ""
```

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | `int` | required | Sequential decision number |
| `title` | `str` | required | Decision title |
| `status` | `DecisionStatus` | `accepted` | Current lifecycle status |
| `date` | `datetime` | now (UTC) | Date the decision was made |
| `author` | `str` | `""` | Decision author |
| `context` | `str` | `""` | Why this decision was needed |
| `decision` | `str` | `""` | What was decided |
| `consequences` | `str` | `""` | Expected consequences |

**Properties:**

| Property | Returns | Description |
|---|---|---|
| `slug` | `str` | URL-safe slug from title (lowercase, max 60 chars) |
| `filename` | `str` | File name: `<id:04d>-<slug>.md` (e.g. `0001-use-postgres.md`) |

**Methods:**

| Method | Description |
|---|---|
| `to_markdown() -> str` | Serialize to ADR markdown format |
| `from_markdown(text, id?) -> Decision` | Parse from ADR markdown (class method) |

---

## Session State

Ephemeral state tracking for the current working session. Stored as
`.context-teleport/state.json`.

### ActiveState

```python
class ActiveState(BaseModel):
    current_task: str = ""
    blockers: list[str] = Field(default_factory=list)
    progress: dict[str, Any] = Field(default_factory=dict)
    last_agent: str = ""
    last_machine: str = ""
    updated_at: datetime = Field(default_factory=now)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `current_task` | `str` | `""` | Description of current task |
| `blockers` | `list[str]` | `[]` | Active blockers |
| `progress` | `dict[str, Any]` | `{}` | Arbitrary progress key-value pairs |
| `last_agent` | `str` | `""` | Last agent that modified state |
| `last_machine` | `str` | `""` | Last machine hostname |
| `updated_at` | `datetime` | now (UTC) | Last update timestamp |

### RoadmapItem

```python
class RoadmapItem(BaseModel):
    title: str
    status: str = "planned"
    milestone: str = ""
```

| Field | Type | Default | Description |
|---|---|---|---|
| `title` | `str` | required | Item title |
| `status` | `str` | `"planned"` | Status string (free-form) |
| `milestone` | `str` | `""` | Associated milestone |

### Roadmap

```python
class Roadmap(BaseModel):
    items: list[RoadmapItem] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=now)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `items` | `list[RoadmapItem]` | `[]` | List of roadmap items |
| `updated_at` | `datetime` | now (UTC) | Last update timestamp |

---

## Preferences

### TeamPreferences

```python
class TeamPreferences(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `values` | `dict[str, Any]` | `{}` | Arbitrary team-wide preference key-value pairs |

### UserPreferences

```python
class UserPreferences(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `values` | `dict[str, Any]` | `{}` | Arbitrary per-user preference key-value pairs |

---

## Session History

Session summaries record what each agent session accomplished. Stored as NDJSON
in `.context-teleport/sessions.ndjson`.

### SessionSummary

```python
class SessionSummary(BaseModel):
    id: str = Field(default_factory=uuid4)
    agent: str = ""
    user: str = ""
    machine: str = ""
    started: datetime = Field(default_factory=now)
    ended: datetime | None = None
    summary: str = ""
    knowledge_added: list[str] = Field(default_factory=list)
    decisions_added: list[str] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | UUID v4 | Session identifier |
| `agent` | `str` | `""` | Agent name (e.g. `claude-code`, `cursor`) |
| `user` | `str` | `""` | User name |
| `machine` | `str` | `""` | Machine hostname |
| `started` | `datetime` | now (UTC) | Session start time |
| `ended` | `datetime \| None` | `None` | Session end time |
| `summary` | `str` | `""` | Free-text session summary |
| `knowledge_added` | `list[str]` | `[]` | Keys of knowledge entries written |
| `decisions_added` | `list[str]` | `[]` | IDs/titles of decisions created |
| `skills_used` | `list[str]` | `[]` | Names of skills used during session (v0.4.0+) |

---

## Skill Tracking (v0.4.0)

Skill tracking data is stored as sidecar files alongside each skill directory:

- `.context-teleport/skills/<name>/.usage.ndjson` -- append-only usage events
- `.context-teleport/skills/<name>/.feedback.ndjson` -- append-only feedback entries
- `.context-teleport/skills/<name>/.proposals/<uuid>.json` -- improvement proposals

All sidecar files are created lazily on first write and synced via git.

### SkillUsageEvent

```python
class SkillUsageEvent(BaseModel):
    id: str = Field(default_factory=uuid4)
    session_id: str = ""
    agent: str = ""
    timestamp: datetime = Field(default_factory=now)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | UUID v4 | Event identifier |
| `session_id` | `str` | `""` | Session that used the skill |
| `agent` | `str` | `""` | Agent that used the skill |
| `timestamp` | `datetime` | now (UTC) | When the skill was used |

### SkillFeedback

```python
class SkillFeedback(BaseModel):
    id: str = Field(default_factory=uuid4)
    agent: str = ""
    rating: int = 3
    comment: str = ""
    timestamp: datetime = Field(default_factory=now)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | UUID v4 | Feedback identifier |
| `agent` | `str` | `""` | Agent providing feedback |
| `rating` | `int` | `3` | Rating from 1 (poor) to 5 (excellent) |
| `comment` | `str` | `""` | Free-text feedback comment |
| `timestamp` | `datetime` | now (UTC) | When feedback was given |

### SkillStats

Read-only aggregated view, computed on the fly from `.usage.ndjson` and `.feedback.ndjson`.

```python
class SkillStats(BaseModel):
    skill_name: str
    usage_count: int = 0
    avg_rating: float = 0.0
    rating_count: int = 0
    last_used: datetime | None = None
    needs_attention: bool = False
```

| Field | Type | Default | Description |
|---|---|---|---|
| `skill_name` | `str` | required | Skill being summarized |
| `usage_count` | `int` | `0` | Total number of usage events |
| `avg_rating` | `float` | `0.0` | Average feedback rating |
| `rating_count` | `int` | `0` | Number of feedback entries |
| `last_used` | `datetime \| None` | `None` | Timestamp of most recent usage |
| `needs_attention` | `bool` | `False` | `True` when `avg_rating < 3.0` and `rating_count >= 2` |

---

## Skill Proposals (v0.4.0)

Improvement proposals stored as individual JSON files under
`.context-teleport/skills/<name>/.proposals/<uuid>.json`.

### ProposalStatus

```python
class ProposalStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    upstream = "upstream"
```

| Value | Description |
|---|---|
| `pending` | Proposal awaiting review |
| `accepted` | Proposal accepted and applied to the skill |
| `rejected` | Proposal rejected |
| `upstream` | Proposal pushed as a PR to an upstream repository |

### SkillProposal

```python
class SkillProposal(BaseModel):
    id: str = Field(default_factory=uuid4)
    skill_name: str
    agent: str = ""
    rationale: str = ""
    proposed_content: str = ""
    diff_summary: str = ""
    status: ProposalStatus = ProposalStatus.pending
    created_at: datetime = Field(default_factory=now)
    resolved_at: datetime | None = None
    resolved_by: str = ""
```

| Field | Type | Default | Description |
|---|---|---|---|
| `id` | `str` | UUID v4 | Proposal identifier |
| `skill_name` | `str` | required | Target skill |
| `agent` | `str` | `""` | Agent that created the proposal |
| `rationale` | `str` | `""` | Why the improvement is needed |
| `proposed_content` | `str` | `""` | Full proposed SKILL.md content |
| `diff_summary` | `str` | `""` | Human-readable diff summary (computed via `difflib`) |
| `status` | `ProposalStatus` | `pending` | Current proposal status |
| `created_at` | `datetime` | now (UTC) | When the proposal was created |
| `resolved_at` | `datetime \| None` | `None` | When the proposal was accepted/rejected |
| `resolved_by` | `str` | `""` | Who resolved the proposal (agent name or `"cli"`) |

---

## Context Scoping

Scope is not a model field but sidecar metadata stored in `.scope.json` files
within each directory (`knowledge/`, `knowledge/decisions/`, `skills/`).

```python
class Scope(str, Enum):
    public = "public"
    private = "private"
    ephemeral = "ephemeral"
```

| Value | Description |
|---|---|
| `public` | Shared with all agents and pushed to remote (default) |
| `private` | Excluded from push and export |
| `ephemeral` | Excluded from push, export, and onboarding |

---

## Schema Versioning

The schema version is stored in `manifest.json` under `schema_version`. Migrations
run automatically when a store is opened with an older version.

### Version History

| Version | Changes |
|---|---|
| `0.1.0` | Initial schema |
| `0.2.0` | Context scoping via `.scope.json` sidecar files |
| `0.3.0` | Multi-agent support: `agent` field on `KnowledgeEntry`, new adapter configs. Backward compatible. |
| `0.4.0` | Skill auto-improvement: usage tracking, feedback, proposals. No-op migration (sidecar files created lazily). |

### Migration Mechanism

Migrations are registered via the `@register_migration(from, to)` decorator in
`ctx.core.migrations`. The `migrate_bundle()` function uses BFS to find the
shortest path between any two versions and applies each step sequentially.

```python
from ctx.core.migrations import SCHEMA_VERSION, migrate_bundle, check_version_compatible

# Check compatibility
check_version_compatible("0.2.0")  # True -- migration path exists

# Migrate bundle data
migrated = migrate_bundle(bundle_data, target_version=SCHEMA_VERSION)
```

All migrations from 0.1.0 through 0.4.0 are backward-compatible no-ops: new fields
have defaults, and new storage (sidecar files, proposal directories) is created lazily
on first write.
