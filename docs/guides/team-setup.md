# Team Setup

This guide walks through setting up Context Teleport for a multi-person team where
multiple developers share project context through a git remote.

## Overview

Context Teleport uses git as its sync transport. Each developer initializes (or joins)
the same `.context-teleport/` store, registers their preferred AI coding tool, and
pushes/pulls context through the shared remote. Agents auto-onboard with the full
project knowledge base on first launch.

## Prerequisites

- Context Teleport installed on each developer's machine (`pip install context-teleport` or `uvx context-teleport`)
- A shared git remote (GitHub, GitLab, any git host)
- At least one supported AI coding tool: Claude Code, Cursor, OpenCode, Codex, or Gemini CLI

## Step 1: Person A initializes the store

The first team member creates the context store with a remote URL:

```bash
cd /path/to/project
context-teleport init --name my-project --repo-url git@github.com:team/my-project-ctx.git
```

This creates the `.context-teleport/` directory structure:

```
.context-teleport/
  manifest.json        # Project metadata and schema version
  knowledge/           # Shared knowledge entries
  knowledge/decisions/ # Architecture Decision Records
  skills/              # Reusable agent skills
  sessions/            # Session logs
```

> **Note:** The `--repo-url` flag configures the git remote for sync. If the project
> is already a git repository, the context store lives inside it. Otherwise, it
> initializes a new git repo.

## Step 2: Person A registers their tool

```bash
context-teleport register claude-code
```

This writes the MCP server configuration into `.claude/mcp.json` (or the equivalent
config for other tools), enabling the agent to read and write context automatically.

If you use multiple tools, you can auto-detect and register all of them:

```bash
context-teleport register
```

## Step 3: Person A works with their agent

Once registered, open your AI coding tool. The agent receives the project context
through the MCP server's dynamic onboarding. Here is an example Claude Code
conversation:

```
You: We decided to use PostgreSQL instead of SQLite for the user service.
     Record this as an architecture decision.

Agent: [calls context_add_decision]
       Recorded decision: "Use PostgreSQL for user service"
       - Context: Evaluated SQLite vs PostgreSQL for production user service
       - Decision: PostgreSQL for concurrent writes and production reliability
       - Consequences: Requires managed database, adds connection pooling dependency

You: Also note that our API uses snake_case for all JSON fields.

Agent: [calls context_set_knowledge]
       Added knowledge entry "api-naming-convention"
```

## Step 4: Person A pushes context

The agent pushes automatically on session end (best-effort), but you can also push
explicitly:

```bash
context-teleport push -m "Initial project context: DB decision, API conventions"
```

Or through the agent:

```
You: Push the context changes.

Agent: [calls context_sync_push]
       Pushed 2 changes to remote.
```

## Step 5: Person B joins the project

Person B clones the project repository, which already contains `.context-teleport/`.
No `init` is needed -- just register:

```bash
cd /path/to/my-project
context-teleport register claude-code
```

That is all. When Person B opens their agent, the MCP server reads the existing store
and provides full project context in the onboarding instructions. The agent immediately
knows about the PostgreSQL decision, the API naming convention, and all other shared
knowledge.

Example conversation for Person B:

```
You: What database are we using for the user service?

Agent: [reads context://knowledge, context://decisions]
       The team decided to use PostgreSQL for the user service.
       This was an architecture decision based on the need for
       concurrent writes and production reliability. SQLite was
       considered but rejected.

You: I'm adding a new caching layer with Redis. Record this decision.

Agent: [calls context_add_decision]
       Recorded decision: "Add Redis caching layer"
```

## Step 6: Ongoing sync

Both developers push and pull as they work. The sync flow is straightforward:

```bash
# Pull latest context before starting work
context-teleport pull

# Push after making changes
context-teleport push
```

Agents handle this automatically through MCP tools (`context_sync_push`,
`context_sync_pull`), but CLI commands are available for explicit control.

## Handling conflicts

When two developers modify the same context entry concurrently, Context Teleport
uses section-level merge for markdown files. If changes are in different `##` sections,
they merge automatically. If the same section was edited, a conflict is reported.

Quick resolution via CLI:

```bash
# Keep your version
context-teleport pull --strategy ours

# Take the remote version
context-teleport pull --strategy theirs

# Resolve interactively in the terminal
context-teleport pull --strategy interactive
```

For a detailed walkthrough of conflict resolution, including the agent-driven
4-step process, see the [Conflict Resolution guide](conflict-resolution.md).

## Recommended practices

1. **Small, focused knowledge entries.** Prefer many small entries over few large
   ones. This reduces merge conflicts since section-level merge operates on `##`
   headers within a single file.

2. **Use decisions for architectural choices.** Decisions are immutable records
   with context, rationale, and consequences. They prevent relitigating settled
   questions.

3. **Pull before starting a session.** Especially on active teams, start each
   session with a pull to get the latest context.

4. **Let agents push on shutdown.** The MCP server attempts a best-effort push
   when the session ends. If you disable this or it fails, run
   `context-teleport push` manually.

5. **Scope sensitive entries as private.** If a knowledge entry is specific to
   your local setup (e.g., local file paths, personal API keys), mark it as
   `private` so it is not pushed to the remote:

   ```
   You: Mark the "local-db-path" knowledge entry as private.

   Agent: [calls context_set_scope("knowledge", "local-db-path", "private")]
   ```

## Checking store status

At any point, verify the state of your context store:

```bash
context-teleport status
```

Output:

```
Context Teleport
  Schema version: 0.4.0
  Store: /path/to/project/.context-teleport
  Knowledge entries: 5
    Keys: api-naming-convention, deployment-targets, ...
  Decisions: 2
  Skills: 3
  Adapters:
    claude-code: enabled
```
