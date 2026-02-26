# Multi-Agent Team

Three developers using different agent tools on a shared project, demonstrating cross-tool context sharing, conflict resolution, and multi-agent coordination.

## Scenario

A team of three is building an e-commerce platform:

- **Alex** uses **Claude Code** (backend, API design)
- **Maria** uses **Cursor** (frontend, React components)
- **Sam** uses **Gemini** (infrastructure, deployment)

All three share a single context store synced via git.

## Setup

### Alex initializes the project

```bash
cd ~/projects/shopfront
context-teleport init --name shopfront --repo-url git@github.com:team/shopfront.git
context-teleport register claude-code
```

### Maria and Sam join

```bash
# Maria
cd ~/projects/shopfront
context-teleport register cursor

# Sam
cd ~/projects/shopfront
context-teleport register gemini
```

Each registration writes the tool's MCP config with the appropriate `MCP_CALLER`:

- Alex's config: `"MCP_CALLER": "mcp:claude-code"`
- Maria's config: `"MCP_CALLER": "mcp:cursor"`
- Sam's config: `"MCP_CALLER": "mcp:gemini"`

## Day 1: Establishing shared context

### Alex (Claude Code) -- API architecture

```
Alex: "Document our API architecture: REST with FastAPI,
       versioned endpoints under /api/v1, OpenAPI docs enabled."

Agent: [calls context_add_knowledge(key="api-architecture", content="...")]
       Knowledge entry saved. (author: mcp:claude-code)

Alex: "Record decision: Use Stripe for payments over building our own"

Agent: [calls context_record_decision(title="Use Stripe for payments", ...)]
       Decision recorded.

Alex: "Push"
Agent: [calls context_sync_push(message="API architecture and Stripe decision")]
```

### Maria (Cursor) -- Frontend patterns

Maria opens Cursor. The agent auto-onboards with Alex's context.

```
Maria: "Pull latest context first"
Agent: [calls context_sync_pull()]
       Pulled. 1 knowledge entry, 1 decision from Alex.

Maria: "Add frontend architecture: React 18 with TypeScript,
        Zustand for state, TanStack Query for server state"

Agent: [calls context_add_knowledge(key="frontend-architecture", content="...")]
       Saved. (author: mcp:cursor)

Maria: "Create a skill for our component pattern"
Agent: [calls context_add_skill(
           name="react-component",
           description="Standard React component with TypeScript and Zustand",
           instructions="..."
       )]

Maria: "Push"
Agent: [calls context_sync_push(message="Frontend architecture and component skill")]
```

### Sam (Gemini) -- Infrastructure

```
Sam: "Pull context"
Agent: [calls context_sync_pull()]
       Got API architecture (from claude-code), frontend architecture (from cursor),
       and react-component skill.

Sam: "Add deployment architecture: Docker Compose for local,
      Kubernetes on GKE for staging and production.
      CI/CD via GitHub Actions."

Agent: [calls context_add_knowledge(key="infrastructure", content="...")]
       [calls context_record_decision(title="GKE over ECS for Kubernetes hosting", ...)]
       Saved. (author: mcp:gemini)
```

## Day 5: Cross-tool skill sharing

Alex creates a backend skill that Maria and Sam can use:

```
Alex: "Create a skill for our API error response format"
Agent: [calls context_add_skill(name="api-errors", description="Standard API error response format", instructions="...")]
Agent: [calls context_sync_push()]
```

Maria pulls and her Cursor agent can now use the same skill:

```
Maria: "I need to handle API errors in the frontend"
Agent: [reads context://skills/api-errors]
       I see the API error format from the backend team.
       Here's a TypeScript error handler that matches...
```

The skill was created by `mcp:claude-code` and consumed by `mcp:cursor` -- seamless cross-tool sharing.

## Day 8: Handling conflicts

Alex and Maria both update the `api-architecture` knowledge entry simultaneously.

### Alex pushes first

```
Alex: "Update API architecture: add WebSocket support for real-time order updates"
Agent: [calls context_add_knowledge(key="api-architecture", content="...updated...")]
Agent: [calls context_sync_push(message="Add WebSocket support")]
       Pushed.
```

### Maria's push conflicts

```
Maria: "Update API architecture: add rate limiting on public endpoints"
Agent: [calls context_add_knowledge(key="api-architecture", content="...updated...")]
Agent: [calls context_sync_push(message="Add rate limiting")]
       Error: push failed, remote has changes.
```

### Resolution with agent strategy

```
Maria: "Pull with agent resolution"
Agent: [calls context_sync_pull(strategy="agent")]
       Conflict in knowledge/api-architecture.md.
       Let me examine it.

       [calls context_conflict_detail(file_path=".context-teleport/knowledge/api-architecture.md")]
       Alex added a WebSocket section, you added a Rate Limiting section.
       These are different sections, so I can merge them cleanly.

       [calls context_resolve_conflict(file_path="...", content="...merged with both sections...")]
       [calls context_merge_finalize()]
       Merged. Both WebSocket support and rate limiting are preserved.
```

Section-level merge handled this automatically because the changes were in different `## ` sections.

## Session handoffs

When Alex finishes for the day and Maria picks up:

```
Alex: "Wrap up, I'm handing off to Maria"
Agent: [calls context_update_state(
           current_task="Implementing order checkout flow",
           blockers="Stripe webhook integration needs testing"
       )]
       [calls context_append_session(
           agent="claude-code",
           summary="Implemented order creation and payment initiation. Webhook handler stubbed.",
           knowledge_added="",
           decisions_added=""
       )]
       [calls context_sync_push()]
```

Maria opens Cursor and asks for the handoff:

```
Maria: "What was Alex working on?"
Agent: [uses context_handoff prompt]
       Alex (claude-code) was working on the order checkout flow.
       Blocker: Stripe webhook integration needs testing.
       He implemented order creation and payment initiation,
       with a stubbed webhook handler.
```

## Attribution tracking

The team can see who wrote what:

```bash
context-teleport knowledge list
# Shows entries with their authors:
#   api-architecture     (mcp:claude-code)
#   frontend-architecture (mcp:cursor)
#   infrastructure       (mcp:gemini)
```

This is tracked in `knowledge/.meta.json` and visible through the CLI and MCP resources.

## Key takeaways

| Pattern | Implementation |
|---------|---------------|
| Shared knowledge | All tools read/write the same store |
| Agent attribution | `MCP_CALLER` env var tags every write |
| Cross-tool skills | SKILL.md format is the same everywhere |
| Conflict resolution | Section-level merge handles most cases automatically |
| Session handoffs | `context_handoff` prompt provides continuity |
| Auto-onboarding | New sessions start with full project context |
