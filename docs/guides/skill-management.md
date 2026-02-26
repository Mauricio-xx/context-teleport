# Skill Management

This guide covers the full lifecycle of agent skills in Context Teleport: creation,
usage tracking, feedback, improvement proposals, and upstream sharing.

## What is a skill?

A skill is a reusable, on-demand capability for AI agents. Unlike knowledge (which
is always included in the agent's context), skills are invoked explicitly when needed.
They are stored as directories under `.context-teleport/skills/`:

```
.context-teleport/
  skills/
    deploy-staging/
      SKILL.md           # Skill definition (frontmatter + body)
      .usage.ndjson      # Usage events (created lazily)
      .feedback.ndjson   # Feedback entries (created lazily)
      .proposals/        # Improvement proposals (created lazily)
        <uuid>.json
```

## SKILL.md format

Every skill is defined by a single `SKILL.md` file with YAML frontmatter and a
markdown body:

```markdown
---
name: deploy-staging
description: Deploy the application to the staging environment
---

## Prerequisites

- Docker daemon running
- kubectl configured for the staging cluster
- Access to the container registry

## Steps

1. Run the test suite:
   ```bash
   pytest tests/ -v
   ```

2. Build and push the image:
   ```bash
   docker build -t registry.example.com/app:staging .
   docker push registry.example.com/app:staging
   ```

3. Apply Kubernetes manifests:
   ```bash
   kubectl apply -f k8s/staging/
   ```

## Verification

Check pod health:
```bash
kubectl get pods -n staging
curl -f https://staging.example.com/health
```

## Rollback

If verification fails:
```bash
kubectl rollout undo deployment/app -n staging
```
```

The frontmatter fields are:

| Field         | Required | Description                              |
|---------------|----------|------------------------------------------|
| `name`        | Yes      | Skill identifier (matches directory name)|
| `description` | Yes      | Short description of the skill's purpose |

The body is free-form markdown containing instructions, code blocks, checklists, or
whatever the agent needs to execute the skill.

## Creating skills

### Via MCP (from within an agent session)

```
You: Create a skill for running database migrations.

Agent: [calls context_add_skill(
         name="db-migrate",
         description="Run database migrations safely with rollback support",
         instructions="## Steps\n\n1. Create a backup: ..."
       )]
       Created skill "db-migrate"
```

### Via CLI

```bash
context-teleport skill add db-migrate \
  --description "Run database migrations safely with rollback support" \
  --file ./migration-instructions.md
```

### Via adapter import

When importing from a tool that has skills, they come along automatically:

```bash
context-teleport import claude-code
# Imports skills from .claude/skills/*/SKILL.md
```

## Listing and reading skills

### CLI

```bash
# List all skills
context-teleport skill list

# Get a specific skill
context-teleport skill get deploy-staging
```

### MCP resources

Agents access skills through MCP resources:

- `context://skills` -- list of all skills with names and descriptions
- `context://skills/{name}` -- full SKILL.md content for a specific skill
- `context://skills/stats` -- usage and rating statistics
- `context://skills/{name}/feedback` -- feedback entries for a skill
- `context://skills/{name}/proposals` -- improvement proposals

## Scoping

Skills support the same scoping system as knowledge entries:

| Scope       | Behavior                                           |
|-------------|----------------------------------------------------|
| `public`    | Default. Synced to remote, included in exports.    |
| `private`   | Not pushed to remote. Local to this machine.       |
| `ephemeral` | Not pushed, not exported. Session-local.           |

Set scope via MCP:

```
Agent: [calls context_set_scope("skill", "deploy-staging", "private")]
```

Or via CLI:

```bash
context-teleport skill scope deploy-staging private
```

## Usage tracking

Every time an agent uses a skill, it should record a usage event. This builds an
adoption and frequency history.

### Recording usage (MCP)

```
Agent: [calls context_report_skill_usage(skill_name="deploy-staging")]

Response:
{
  "status": "ok",
  "event_id": "evt-a1b2c3d4"
}
```

Usage events are appended to `.usage.ndjson` inside the skill directory. Each event
records:

- Event ID
- Session ID (if available)
- Agent identity (from `MCP_CALLER`)
- Timestamp

### Viewing usage stats

```bash
context-teleport skill stats
```

Output:

```
Skill             Uses  Avg Rating  Needs Attention
deploy-staging      12        4.2   No
db-migrate           8        2.5   Yes
code-review          3        4.8   No
lint-fix             0         --   --
```

The `--sort` flag controls ordering:

```bash
context-teleport skill stats --sort usage    # Most used first
context-teleport skill stats --sort rating   # Highest rated first
context-teleport skill stats --sort name     # Alphabetical
```

## Feedback and ratings

Agents rate skills on a 1-5 scale with optional comments. This provides signal on
which skills are helpful and which need improvement.

### Rating a skill (MCP)

```
Agent: [calls context_rate_skill(
         skill_name="db-migrate",
         rating=2,
         comment="Migration rollback steps are outdated, references old schema tool"
       )]

Response:
{
  "status": "ok",
  "feedback_id": "fb-e5f6g7h8"
}
```

Feedback entries are appended to `.feedback.ndjson`. Each entry includes:

- Feedback ID
- Agent identity
- Rating (1-5)
- Comment (optional)
- Timestamp

### Viewing feedback

```bash
context-teleport skill feedback db-migrate
```

Output:

```
Date                 Agent            Rating  Comment
2025-07-10 14:30     mcp:claude-code       2  Migration rollback steps are outdated
2025-07-11 09:15     mcp:cursor            3  Works but slow, needs optimization
2025-07-12 11:00     mcp:claude-code       2  Still referencing old schema tool
```

## Review: finding skills that need attention

Skills are flagged as "needs attention" when they have an average rating below 3.0
with at least 2 ratings. This prevents a single bad rating from triggering a review.

```bash
context-teleport skill review
```

Output:

```
Skills needing review:

  db-migrate
    Average rating: 2.3 (3 ratings, 8 uses)
    Recent feedback:
      - [2] Migration rollback steps are outdated
      - [3] Works but slow, needs optimization
      - [2] Still referencing old schema tool
```

If no skills need attention, the command reports that all skills are healthy.

## Improvement proposals

When a skill needs improvement, agents can propose changes rather than modifying the
skill directly. Proposals go through a review process before being applied.

### Creating a proposal (MCP)

```
Agent: [calls context_propose_skill_improvement(
         skill_name="db-migrate",
         proposed_content="---\nname: db-migrate\ndescription: ...\n---\n\n## Steps\n...",
         rationale="Updated rollback steps to use new schema tool, added pre-migration backup verification"
       )]

Response:
{
  "status": "ok",
  "proposal_id": "prop-i9j0k1l2",
  "diff_summary": "--- current\n+++ proposed\n@@ -15,7 +15,9 @@..."
}
```

The proposal stores:

- Full proposed `SKILL.md` content
- Rationale for the change
- Computed diff summary (via `difflib`)
- Agent identity and timestamp
- Status: `pending` (initial), `accepted`, `rejected`, or `upstream`

### Listing proposals

```bash
context-teleport skill proposals
```

Output:

```
Skill         ID             Agent            Status   Rationale
db-migrate    prop-i9j0k1l2  mcp:claude-code  pending  Updated rollback steps...
code-review   prop-m3n4o5p6  mcp:cursor       pending  Added security checklist...
```

Filter by skill or status:

```bash
context-teleport skill proposals --skill db-migrate
context-teleport skill proposals --status pending
```

### Accepting or rejecting proposals

```bash
# Accept: applies the proposed content to the skill
context-teleport skill apply-proposal db-migrate prop-i9j0k1l2

# Reject: marks the proposal as rejected without changing the skill
context-teleport skill apply-proposal db-migrate prop-i9j0k1l2 --reject
```

When accepted, the proposal's `proposed_content` replaces the current `SKILL.md` and
the proposal status changes to `accepted`.

## Upstream proposals

For teams that maintain shared skill packs (separate git repositories with reusable
skills), you can push a proposal upstream as a pull request:

```bash
context-teleport skill propose-upstream db-migrate prop-i9j0k1l2 \
  --repo team/shared-skills
```

This:

1. Clones the upstream repository
2. Creates a branch with the proposed changes
3. Opens a pull request via the `gh` CLI

The proposal status changes to `upstream`, linking it to the PR.

> **Prerequisite:** The `gh` CLI must be installed and authenticated
> (`gh auth login`).

## Dynamic instructions

The MCP server integrates skill health into its startup onboarding. When the server
generates instructions for the connected agent, it appends a notice if any skills
need attention:

```
Skills needing review: db-migrate, legacy-deploy.
```

This prompts the agent to check on those skills and potentially propose improvements,
closing the feedback loop automatically.

## Lifecycle summary

```
Create skill
    |
    v
Agent uses skill -> records usage event
    |
    v
Agent rates skill -> records feedback
    |
    v
Skill stats aggregated (usage count, avg rating)
    |
    v
Needs attention? (avg < 3.0, 2+ ratings)
    |
    +-- No -> continue using
    |
    +-- Yes -> Agent proposes improvement
                  |
                  v
              Human reviews proposal
                  |
                  +-- Accept -> skill updated
                  |
                  +-- Reject -> proposal archived
                  |
                  +-- Upstream -> PR to shared skill pack
```

## CLI reference

```bash
# List all skills
context-teleport skill list

# View a skill
context-teleport skill get <name>

# Add or update a skill
context-teleport skill add <name> --description "..." --file <path>

# Remove a skill
context-teleport skill rm <name>

# Set skill scope
context-teleport skill scope <name> public|private|ephemeral

# View usage/rating statistics
context-teleport skill stats [--sort usage|rating|name]

# View feedback for a skill
context-teleport skill feedback <name>

# Show skills needing attention
context-teleport skill review

# List improvement proposals
context-teleport skill proposals [--skill NAME] [--status STATUS]

# Accept or reject a proposal
context-teleport skill apply-proposal <skill> <id> [--reject]

# Push proposal upstream as a PR
context-teleport skill propose-upstream <skill> <id> --repo OWNER/REPO
```

## MCP tools reference

| Tool                                | Description                              |
|-------------------------------------|------------------------------------------|
| `context_add_skill`                 | Create or update a skill                 |
| `context_remove_skill`              | Delete a skill                           |
| `context_report_skill_usage`        | Record a usage event                     |
| `context_rate_skill`                | Rate a skill (1-5) with optional comment |
| `context_propose_skill_improvement` | Propose changes to a skill               |
| `context_list_skill_proposals`      | List proposals with optional filters     |

## MCP resources reference

| Resource                              | Description                    |
|---------------------------------------|--------------------------------|
| `context://skills`                    | List of all skills             |
| `context://skills/{name}`             | Full SKILL.md content          |
| `context://skills/stats`              | Usage and rating statistics    |
| `context://skills/{name}/feedback`    | Feedback entries for a skill   |
| `context://skills/{name}/proposals`   | Proposals for a skill          |
