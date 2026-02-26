# MCP Prompts

Context Teleport exposes **4 MCP prompts** that generate structured, multi-section text from the current store state. Prompts are read-only and return markdown-formatted strings. They are designed for specific agent workflows: session start, session handoff, decision review, and conflict resolution.

---

## `context_onboarding`

Full project context for a new agent session.

**When to use:** At the start of every agent session to load the complete project context. This is the primary onboarding mechanism and the recommended first action for any agent connecting to the MCP server.

**Description:** Assembles the public knowledge base, architectural decisions, available skills, current session state, and the 5 most recent session summaries into a single, structured document. Only entries with `public` scope are included.

**Output structure:**

```markdown
# Project: my-project
Schema version: 0.4.0

## Knowledge Base

### architecture
Microservices with gRPC communication between services...

### tech-stack
Python 3.12, FastAPI, PostgreSQL 16...

## Architectural Decisions

### ADR-0001: Use PostgreSQL for persistence (accepted)
**Context:** Need ACID transactions and JSON support
**Decision:** PostgreSQL 16 with pgvector extension
**Consequences:** Team needs PostgreSQL expertise

### ADR-0002: Adopt gRPC for service communication (proposed)
**Context:** REST has too much overhead for internal calls
**Decision:** gRPC with protobuf for all inter-service calls
**Consequences:** Adds protobuf compilation step to CI

## Agent Skills

- **deploy-staging**: Deploy the application to staging environment
- **run-tests**: Execute the full test suite with coverage

## Current State
- Task: Implementing auth middleware
- Blockers: Waiting for API spec

## Recent Sessions
- [claude-code] Set up database schema and migrations
- [cursor] Added integration test suite
- [claude-code] Initial project scaffolding
```

**Sections included:**

| Section | Content | Condition |
|---------|---------|-----------|
| Header | Project name, schema version | Always |
| Knowledge Base | All public knowledge entries with full content | If any public knowledge exists |
| Architectural Decisions | All public decisions with context/decision/consequences | If any public decisions exist |
| Agent Skills | Name and description of all public skills | If any public skills exist |
| Current State | Active task and blockers | If a current task is set |
| Recent Sessions | Last 5 session summaries with agent labels | If any sessions exist |

!!! tip "Dynamic server instructions"
    The MCP server also generates a shorter version of this context as its `instructions` field, which many MCP clients display automatically. The `context_onboarding` prompt provides the full, detailed version.

---

## `context_handoff`

Session handoff summary for the next agent.

**When to use:** At the end of a session (or when switching between agents) to capture the current state for smooth continuation. Also useful when an agent needs to understand what the previous agent was doing without loading the full knowledge base.

**Description:** Focuses on the current working state: active task, blockers, progress tracking, and the 3 most recent session summaries. Unlike `context_onboarding`, this prompt does not include knowledge or decision content -- it is optimized for quick state transfer.

**Output structure:**

```markdown
# Session Handoff

## Current State
- Working on: Implementing auth middleware
- Blockers: Waiting for API spec, Redis not configured
- Progress:
  - auth: 50%
  - tests: done
  - docs: not started

## Recent Sessions
- [claude-code] Set up database schema and migrations
- [cursor] Added integration test suite
- [claude-code] Initial project scaffolding
```

**Sections included:**

| Section | Content | Condition |
|---------|---------|-----------|
| Current State | Active task, blockers, progress map | Always (shows "No active task" if empty) |
| Recent Sessions | Last 3 session summaries | If any sessions exist |

---

## `context_review_decisions`

All architectural decisions with full detail for review.

**When to use:** Before making a new architectural decision, to review all existing decisions and avoid contradictions or duplicates. Also useful for periodic decision audits.

**Description:** Lists every decision (regardless of scope) with its full metadata: status, date, author, context, decision text, and consequences. Decisions are presented in order of their ID, separated by horizontal rules.

**Output structure:**

```markdown
# Architectural Decisions Review

## ADR-0001: Use PostgreSQL for persistence
**Status:** accepted
**Date:** 2025-05-01
**Author:** claude-code

### Context
Need ACID transactions and JSON support for our data model.

### Decision
PostgreSQL 16 with pgvector extension for vector similarity search.

### Consequences
Team needs PostgreSQL expertise. Adds infrastructure complexity.

---

## ADR-0002: Adopt gRPC for service communication
**Status:** proposed
**Date:** 2025-05-05
**Author:** cursor

### Context
REST has too much overhead for internal service-to-service calls.

### Decision
gRPC with protobuf for all inter-service communication.

### Consequences
Adds protobuf compilation step to CI pipeline.

---
```

**Fields per decision:**

| Field | Source | Always present |
|-------|--------|----------------|
| Title | `Decision.title` | Yes |
| Status | `Decision.status` (`proposed`, `accepted`, `deprecated`, `superseded`) | Yes |
| Date | `Decision.date` (formatted `YYYY-MM-DD`) | Yes |
| Author | `Decision.author` | Only if set |
| Context | `Decision.context` | Only if set |
| Decision | `Decision.decision` | Only if set |
| Consequences | `Decision.consequences` | Only if set |

**Empty state:** Returns `"No decisions recorded yet."` if no decisions exist.

---

## `context_resolve_conflicts`

Conflict resolution guide with per-file summaries and step-by-step instructions.

**When to use:** After `context_sync_pull(strategy="agent")` returns conflicts. This prompt provides the agent with everything it needs to understand and resolve each conflict.

**Description:** Reads the persisted conflict state from `.context-teleport/.pending_conflicts.json` and generates a structured resolution guide. Includes a conflict overview, per-file status with content size information, resolution steps, and merge guidelines.

**Output structure:**

```markdown
# Merge Conflict Resolution Guide

**Conflict ID:** h7i8j9k0-...
**Total conflicts:** 3
**Unresolved:** 2
**Auto-resolved:** 1

## Conflicted Files

- `.context-teleport/knowledge/architecture.md` [UNRESOLVED] (markdown, ours: 1234 chars, theirs: 1456 chars)
- `.context-teleport/knowledge/tech-stack.md` [UNRESOLVED] (markdown, ours: 567 chars, theirs: 890 chars)
- `.context-teleport/state/active.json` [resolved] (other, ours: 200 chars, theirs: 250 chars)

## Resolution Steps

1. **Examine each file:** Call `context_conflict_detail(file_path)` for each unresolved file
2. **Resolve:** Call `context_resolve_conflict(file_path, content)` with the merged content
3. **Finalize:** Call `context_merge_finalize()` to commit the merge

## Merge Guidelines

- **Combine knowledge:** merge complementary information from both sides
- **Never drop decisions:** if both sides added different ADRs, keep both
- **Prefer newer data:** for state/progress fields, the more recent update wins
- **Preserve structure:** maintain section headers and formatting
- If section_analysis shows no conflicts, use the auto_merged_content directly

To abort the merge instead: call `context_merge_abort()`
```

**Pre-conditions:**

- Requires an active conflict state from a prior `context_sync_pull(strategy="agent")` call
- If no pending conflicts exist, returns: `"No pending merge conflicts. Use context_sync_pull(strategy='agent') to pull with conflict detection."`
- If not in a git repository, returns: `"Error: not in a git repository."`

!!! info "Resolution workflow"
    The typical agent workflow after receiving this prompt:

    1. Read the prompt to understand the conflict scope
    2. Call `context_conflict_detail(file_path)` for each unresolved file
    3. For markdown files, check if `section_analysis.auto_merged_content` is available
    4. Call `context_resolve_conflict(file_path, content)` with the merged result
    5. Call `context_merge_finalize()` to commit
    6. Or call `context_merge_abort()` to discard
