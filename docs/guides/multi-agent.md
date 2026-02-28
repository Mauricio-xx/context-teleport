# Multi-Agent Workflows

This guide covers running multiple AI coding tools on the same project, sharing a
single Context Teleport store. Each agent reads and writes to the same knowledge base,
with attribution tracking who contributed what.

## Why multi-agent?

Different tools have different strengths. You might use Claude Code for backend logic,
Cursor for frontend iteration, and Gemini CLI for documentation review. Context Teleport
lets all of them share the same project knowledge without manual copy-paste between
tool-specific config files.

## Agent identity tracking

Every MCP server registration sets the `MCP_CALLER` environment variable, which
identifies the calling agent:

| Tool        | MCP_CALLER value    |
|-------------|---------------------|
| Claude Code | `mcp:claude-code`   |
| Cursor      | `mcp:cursor`        |
| OpenCode    | `mcp:opencode`      |
| Gemini      | `mcp:gemini`        |
| Codex       | (MCP not supported) |

When an agent writes a knowledge entry, records a decision, or creates a skill, the
`agent` field in the metadata is set automatically. This is how you trace who wrote
what.

Example metadata in `knowledge/.meta.json`:

```json
{
  "api-conventions": {
    "author": "mcp:claude-code",
    "updated_at": "2025-07-15T10:30:00Z"
  },
  "frontend-state-management": {
    "author": "mcp:cursor",
    "updated_at": "2025-07-15T14:22:00Z"
  }
}
```

## Registering multiple tools

Register each tool individually:

```bash
context-teleport register claude-code
context-teleport register cursor
context-teleport register gemini
```

Or auto-detect all available tools at once:

```bash
context-teleport register
```

This scans for each tool's config file presence (e.g., `.claude/` directory, `.cursor/`
directory, `.gemini/` directory) and registers the MCP server for every detected tool.

> **Note:** Codex does not support MCP server registration. Codex reads context via
> export to `AGENTS.md` and `.codex/instructions.md`. Use
> `context-teleport export codex` to push context to Codex's format.

## Example: Backend + Frontend workflow

### Setup

```bash
cd /path/to/fullstack-project
context-teleport init --name fullstack-app
context-teleport register claude-code
context-teleport register cursor
```

### Backend session (Claude Code)

```
You: We're implementing a REST API with FastAPI. The auth
     middleware uses JWT tokens with RS256 signing.
     Record this as knowledge.

Agent: [calls context_add_knowledge("auth-middleware", ...)]
       (agent field: "mcp:claude-code")
       Added knowledge entry "auth-middleware"

You: Record a decision: we chose FastAPI over Flask for
     async support and automatic OpenAPI generation.

Agent: [calls context_add_decision]
       (agent field: "mcp:claude-code")
       Recorded decision: "FastAPI over Flask"
```

### Frontend session (Cursor)

When Cursor opens, its MCP server reads the same `.context-teleport/` store. The
onboarding instructions include the auth-middleware knowledge and the FastAPI decision
automatically.

```
You: The frontend needs to call the auth endpoint.
     What signing algorithm does the backend use?

Agent: [reads context://knowledge/auth-middleware]
       The backend uses JWT tokens with RS256 signing.
       You'll need the public key for token verification
       on the client side.

You: We're using React Query for all API calls. Add this
     to the project knowledge.

Agent: [calls context_add_knowledge("frontend-data-fetching", ...)]
       (agent field: "mcp:cursor")
       Added knowledge entry "frontend-data-fetching"
```

Both agents now see both entries. Claude Code sees the React Query choice, Cursor
sees the JWT details.

## Session handoff between agents

When switching from one agent to another mid-task, use the `context_handoff` prompt
to generate a session summary for the next agent:

```
You: Generate a handoff summary for the next session.

Agent: [calls context_handoff prompt]

# Session Handoff

## Current State
- Working on: JWT auth integration
- Progress:
  - backend-auth: complete
  - frontend-token-handling: in progress

## Recent Sessions
- [mcp:claude-code] Implemented RS256 JWT middleware
- [mcp:cursor] Started React Query integration for auth endpoints
```

The next agent (regardless of which tool) can read this handoff to continue where the
previous session left off.

## Lifecycle hooks (Claude Code)

When you run `context-teleport register claude-code`, the adapter installs lifecycle hooks into `.claude/settings.json`. These hooks keep the agent context-aware across session events without requiring manual intervention.

### Installed hooks

| Hook | Event | Behavior |
|------|-------|----------|
| **PreCompact** | Before context compaction | Reminds the agent to save important context to the store before the window is compressed |
| **SessionStart** (compact) | Session resumes after compaction | Directs the agent to the `context_onboarding` prompt to re-orient with project context |
| **SubagentStart** | Subagent is spawned | Injects project context awareness into subagents so they know Context Teleport is available |

### Why hooks matter

Without hooks, an agent that undergoes context compaction loses awareness of the context store entirely. It will not call MCP tools unless reminded. The PreCompact hook acts as a safety net, and the SessionStart hook ensures the agent re-reads project context after compaction.

The SubagentStart hook solves a different problem: subagents (spawned by the main agent for parallel tasks) start with no knowledge of the project's context store. The hook injects a brief instruction so subagents can use Context Teleport tools.

### Uninstalling hooks

Hooks are removed automatically by `context-teleport unregister claude-code`. They can also be manually edited in `.claude/settings.json` -- Context Teleport hooks are prefixed with identifiable markers.

## Viewing agent contributions

Check which agent wrote which entries via the CLI:

```bash
context-teleport status --format json | jq '.knowledge'
```

Or through the MCP resources:

```
You: Show me all knowledge entries and who wrote them.

Agent: [reads context://knowledge]
       - auth-middleware (by mcp:claude-code)
       - frontend-data-fetching (by mcp:cursor)
       - api-conventions (by mcp:claude-code)
```

## Concurrent sessions

Multiple agents can be open simultaneously. They all read from the same
`.context-teleport/` directory on disk. Writes are atomic at the file level (each
knowledge entry is a separate `.md` file, each skill is a separate directory).

However, if two agents write to the *same* entry at the *same* time, the last write
wins on disk. For git-synced teams, the conflict resolution system handles divergent
remote changes. For local-only usage, avoid having two agents edit the same entry
concurrently.

> **Tip:** Use the `context-teleport watch` command to monitor the store for changes
> in real time. This is useful for debugging multi-agent scenarios where you want to
> see writes as they happen.

## Skills across agents

Skills are a cross-tool standard. A skill created by Claude Code:

```
skills/
  deploy-staging/
    SKILL.md     # YAML frontmatter + markdown body
    .usage.ndjson
    .feedback.ndjson
```

...is immediately available to Cursor, OpenCode, and Gemini through the same MCP
server. Usage tracking and feedback are attributed to the agent that performed the
action.

```
You (in Cursor): Use the deploy-staging skill.

Agent: [reads context://skills/deploy-staging, calls context_report_skill_usage]
       (usage event recorded with agent: "mcp:cursor")
```

See the [Skill Management guide](skill-management.md) for the full skill lifecycle.

## Non-MCP tools (Codex)

Codex does not support MCP, so it cannot connect to the live context store. Instead,
use the export/import cycle:

```bash
# Push store content to Codex-readable files
context-teleport export codex

# After working in Codex, pull changes back
context-teleport import codex
```

This writes knowledge to `AGENTS.md` and `.codex/instructions.md` with managed
sections marked by `<!-- ctx:start -->` / `<!-- ctx:end -->` markers. Codex reads
those files natively.

## Architecture summary

```
  Claude Code          Cursor            Gemini CLI
       |                  |                  |
       v                  v                  v
   MCP Server         MCP Server         MCP Server
   (MCP_CALLER:       (MCP_CALLER:       (MCP_CALLER:
    claude-code)       cursor)            gemini)
       \                 |                  /
        \                |                 /
         +--------> .context-teleport/ <--+
                     (shared store)
                          |
                      git push/pull
                          |
                     remote repo
```

All agents read/write the same store. The `MCP_CALLER` environment variable is the
only difference, ensuring each write is properly attributed.
