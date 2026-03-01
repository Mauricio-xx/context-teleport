# Context Governance

All hard limits and budget controls that shape how Context Teleport manages store content.

## Onboarding Budget

The MCP server builds a dynamic instruction string at startup. These caps prevent the agent's context window from being overwhelmed on large stores. Full data is always available via resources (`context://knowledge`, `context://skills`, etc.).

| Limit | Value | Constant | Source |
|-------|-------|----------|--------|
| Knowledge entries in onboarding | 30 | `MAX_ONBOARDING_KNOWLEDGE` | `src/ctx/mcp/server.py` |
| Decisions in onboarding | 20 | `MAX_ONBOARDING_DECISIONS` | `src/ctx/mcp/server.py` |
| Conventions in onboarding | 20 | `MAX_ONBOARDING_CONVENTIONS` | `src/ctx/mcp/server.py` |
| Skills in onboarding | 30 | `MAX_ONBOARDING_SKILLS` | `src/ctx/mcp/server.py` |
| Inline keys per content type | 15 | `MAX_INSTRUCTION_KEYS` | `src/ctx/mcp/server.py` |
| Content truncation per entry | 2000 chars | `MAX_ONBOARDING_CONTENT_CHARS` | `src/ctx/mcp/server.py` |

When an entry is truncated, a `... (truncated, see full entry via resource)` marker is appended. When more keys exist than the inline limit, a `... and N more` suffix is shown.

## Store Limits

| Limit | Value | Constant | Source |
|-------|-------|----------|--------|
| Session history cap | 200 entries | `MAX_SESSIONS` | `src/ctx/core/store.py` |
| Activity stale threshold | 48 hours | `ACTIVITY_STALE_HOURS` | `src/ctx/core/schema.py` |

The session history file (`history/sessions.ndjson`) is pruned to the last 200 entries on every append. This prevents unbounded growth in long-lived projects.

Activity entries older than 48 hours are flagged as stale in onboarding instructions. Stale entries are not deleted -- they remain visible but carry a `(stale)` marker.

## Content Types Without TTL

Knowledge entries, decisions, conventions, and skills have **no automatic expiration**. They persist indefinitely until explicitly removed.

Prescribed approaches for managing content growth:

- **Manual removal**: `context-teleport knowledge rm <key>`, `context-teleport convention rm <key>`, etc.
- **Ephemeral scope**: Set `scope=ephemeral` on entries that should not survive sync. Ephemeral entries are excluded from git push.
- **Private scope**: Set `scope=private` to keep entries local (not synced to team, not shown in onboarding).

## Sync Scope Filtering

The git sync engine respects scope metadata:

| Scope | Included in push | Included in onboarding | Included in export |
|-------|-----------------|----------------------|-------------------|
| `public` (default) | Yes | Yes | Yes |
| `private` | No | No | No |
| `ephemeral` | No | No | No |

Activity entries are always public and always synced.

## Skill Auto-Improvement Thresholds

| Threshold | Value | Description |
|-----------|-------|-------------|
| Needs attention | avg rating < 3.0 | Flagged in `skill review` and onboarding instructions |
| Minimum ratings | 2 | A skill needs at least 2 feedback entries before being evaluated |
| Rating range | 1--5 | Integer scale for `context_rate_skill` |
