# Quickstart

Get Context Teleport running in your project in under 5 minutes. By the end of this page, your agent will have a shared context store it can read and write through natural language.

## 1. Initialize the store

Navigate to your project root and create a context store:

=== "uvx"

    ```bash
    cd ~/my-project
    uvx context-teleport init --name my-project
    ```

=== "pip install"

    ```bash
    cd ~/my-project
    context-teleport init --name my-project
    ```

This creates a `.context-teleport/` directory inside your project with a `manifest.json`, empty `knowledge/`, `decisions/`, and `skills/` directories, and a `state/` directory for session tracking.

```
my-project/
  .context-teleport/
    manifest.json
    knowledge/
    decisions/
    skills/
    state/
    sessions/
```

!!! tip "Project name"
    The `--name` flag sets the project name stored in the manifest. If omitted, it defaults to the directory name.


## 2. Register with your agent tool

Register the MCP server so your agent can discover and use it:

=== "Claude Code"

    ```bash
    context-teleport register claude-code
    ```

    This writes to `.claude/mcp.json` in your project.

=== "Cursor"

    ```bash
    context-teleport register cursor
    ```

    This writes to `.cursor/mcp.json` in your project.

=== "Gemini"

    ```bash
    context-teleport register gemini
    ```

    This writes to `.gemini/settings.json` in your project.

=== "OpenCode"

    ```bash
    context-teleport register opencode
    ```

    This writes to `opencode.json` in your project.

=== "Auto-detect"

    ```bash
    context-teleport register
    ```

    Without a tool name, Context Teleport detects which tools are present and registers with all of them.

After registration, the agent tool spawns the MCP server automatically when it starts a session. You do not need to run anything manually.


## 3. Open your agent and start working

Launch your agent tool in the project directory. Context Teleport provides auto-onboarding: on session start, the agent receives a summary of the project's knowledge, decisions, skills, current task, and recent history.

Here is what a typical interaction looks like:

### Save knowledge

```
You: "Save that we're using hexagonal architecture with FastAPI for the backend"
Agent: [calls context_add_knowledge with key="architecture" and content="..."] Done.
```

The agent writes a markdown file at `.context-teleport/knowledge/architecture.md` with the content you described.

### Record a decision

```
You: "Record the decision to use PostgreSQL over MongoDB for the primary database"
Agent: [calls context_record_decision with title, context, decision, consequences]
      Decision ADR-0001 recorded.
```

Decisions follow an ADR (Architecture Decision Record) format with structured fields for context, the decision itself, and expected consequences.

### Create a skill

```
You: "Create a skill for our deploy-staging workflow"
Agent: [calls context_add_skill with name="deploy-staging", description, instructions]
      Skill 'deploy-staging' saved.
```

Skills are reusable agent capabilities stored as SKILL.md files with YAML frontmatter and markdown instructions.

### Search context

```
You: "What do we know about authentication?"
Agent: [calls context_search with query="authentication"]
      Found 2 results: knowledge/auth-strategy.md (line 3, score 0.95),
      decisions/0002.md (line 12, score 0.72)
```

### Sync with the team

```
You: "Sync context with the team"
Agent: [calls context_sync_push] Pushed 3 changes to remote.
```

```
You: "Pull latest context"
Agent: [calls context_sync_pull] Pulled 2 changes. No conflicts.
```


## 4. Check what you have

From the terminal, you can inspect the store at any time:

```bash
context-teleport status
```

This shows the project name, schema version, number of knowledge entries, decisions, skills, current task, and registered adapters.

You can also list entries directly:

```bash
# List all knowledge entries
context-teleport knowledge list

# Read a specific entry
context-teleport knowledge get architecture

# List all decisions
context-teleport decision list

# List all skills
context-teleport skill list
```


## What happens under the hood

1. **init** creates the `.context-teleport/` directory with a versioned manifest and empty content directories
2. **register** writes an MCP server entry to the tool's config file, pointing to `context-teleport` (via `uvx` or local path)
3. When the agent starts, it spawns `context-teleport` over stdio as an MCP server
4. The server auto-generates onboarding instructions from the store state
5. The agent reads context via MCP resources (`context://knowledge`, `context://decisions`, etc.)
6. The agent writes context via MCP tools (`context_add_knowledge`, `context_record_decision`, etc.)
7. Sync operations commit to the local git repo and push/pull from the remote

!!! info "Git integration"
    The `.context-teleport/` directory lives inside your git repository. Sync operations (`push`/`pull`) commit context changes to a branch and push them to your remote. If there is no remote configured, push still commits locally so nothing is lost.


## Next steps

- **[First Project](first-project.md)** -- Extended tutorial covering the full lifecycle: remote setup, team onboarding, skills, sync, and conflict handling
- **[Adapter Workflows](../guides/adapter-workflows.md)** -- Import existing context from Claude Code, Cursor, Gemini, or other tools
- **[Skill Management](../guides/skill-management.md)** -- Create, share, and improve reusable agent skills
- **[Team Setup](../guides/team-setup.md)** -- Configure git remotes and team workflows
