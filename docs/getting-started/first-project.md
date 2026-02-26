# First Project

This tutorial walks through the full Context Teleport lifecycle -- from initializing a store with a git remote, through building up project context, to onboarding a second team member and handling sync conflicts. It assumes you have already [installed Context Teleport](installation.md).


## 1. Initialize with a remote

Create a git repository for your project's context (or use an existing one). Then initialize the store with a remote URL:

```bash
cd ~/my-project
context-teleport init --name my-project --repo-url git@github.com:team/my-project.git
```

This does two things:

1. Creates the `.context-teleport/` directory with the store structure
2. Configures the git remote for sync operations

!!! info "Using an existing git repo"
    If your project already has a git repository, Context Teleport uses it directly. The `.context-teleport/` directory becomes part of your project's git tree. The `--repo-url` flag sets the remote for sync operations -- if your repo already has an `origin` remote, you can skip it.

Verify the setup:

```bash
context-teleport status
```

You should see the project name, schema version, and zero entries for knowledge, decisions, and skills.


## 2. Register your agent tool

Register the MCP server with whatever agent tool you use:

```bash
context-teleport register claude-code
```

!!! tip "Multiple tools"
    If your team uses different agent tools, each person registers their own. The context store is tool-agnostic -- a Claude Code user and a Cursor user share the same `.context-teleport/` directory:

    ```bash
    # Person A
    context-teleport register claude-code

    # Person B
    context-teleport register cursor
    ```


## 3. Build up knowledge

Open your agent tool and start capturing project context. Knowledge entries are freeform markdown keyed by a short identifier.

### Architecture

```
You: "Save our architecture: we use a hexagonal architecture pattern.
      The core domain has no framework dependencies. FastAPI handles HTTP,
      SQLAlchemy handles persistence, and all external services are behind
      port interfaces."

Agent: [calls context_add_knowledge]
       Saved knowledge entry 'architecture'.
```

### Tech stack

```
You: "Record our tech stack: Python 3.12, FastAPI, SQLAlchemy 2.0,
      PostgreSQL 16, Redis for caching, Docker Compose for local dev,
      deployed on AWS ECS with Terraform."

Agent: [calls context_add_knowledge]
       Saved knowledge entry 'tech-stack'.
```

### Deployment

```
You: "Document our deployment process: we use GitHub Actions for CI.
      Merges to main deploy to staging automatically. Production deploys
      require a manual approval step in the pipeline. Rollbacks are done
      by reverting the merge commit."

Agent: [calls context_add_knowledge]
       Saved knowledge entry 'deployment'.
```

You can verify what was saved from the CLI at any time:

```bash
context-teleport knowledge list
context-teleport knowledge get architecture
```


## 4. Record architectural decisions

Decisions use an ADR (Architecture Decision Record) structure with four fields: title, context, decision, and consequences.

### Database choice

```
You: "Record the decision to use PostgreSQL:
      Context: We need ACID transactions, complex queries with joins,
      and strong data consistency. The team has extensive PostgreSQL experience.
      Decision: Use PostgreSQL 16 as the primary database.
      Consequences: We get mature tooling, great performance for our workload,
      and the team can be productive immediately. We lose the schema flexibility
      of a document store."

Agent: [calls context_record_decision]
       Decision ADR-0001 recorded: 'Use PostgreSQL as primary database'
```

### Authentication strategy

```
You: "Record the decision to use JWT with refresh tokens:
      Context: The API serves both a web frontend and mobile apps.
      We need stateless auth that works across clients.
      Decision: JWT access tokens (15min TTL) with opaque refresh tokens
      stored in PostgreSQL.
      Consequences: Stateless verification on most requests. Refresh token
      rotation provides revocation capability. Slightly more complex than
      session cookies but works well for multi-client scenarios."

Agent: [calls context_record_decision]
       Decision ADR-0002 recorded: 'JWT with refresh tokens for authentication'
```

List decisions from the CLI:

```bash
context-teleport decision list
```


## 5. Create a skill

Skills are reusable agent capabilities -- think of them as instructions the agent can follow on demand. They are stored as SKILL.md files with YAML frontmatter and a markdown body.

```
You: "Create a skill called 'deploy-staging' for deploying to the staging
      environment. Description: 'Deploy current branch to staging via CI'.
      Instructions:
      1. Ensure all tests pass locally: pytest tests/ -v
      2. Push the current branch to origin
      3. Open a PR targeting the 'staging' branch
      4. Verify the GitHub Actions workflow starts
      5. Check the deployment URL: https://staging.example.com/health
      6. If health check fails, check CloudWatch logs in the staging account"

Agent: [calls context_add_skill]
       Skill 'deploy-staging' saved.
```

Skills live in `.context-teleport/skills/deploy-staging/SKILL.md` and look like this:

```yaml
---
name: deploy-staging
description: Deploy current branch to staging via CI
---

1. Ensure all tests pass locally: `pytest tests/ -v`
2. Push the current branch to origin
3. Open a PR targeting the `staging` branch
4. Verify the GitHub Actions workflow starts
5. Check the deployment URL: https://staging.example.com/health
6. If health check fails, check CloudWatch logs in the staging account
```

You can also manage skills from the CLI:

```bash
context-teleport skill list
context-teleport skill get deploy-staging
```


## 6. Push to remote

Once you have built up some context, push it to the git remote so your team can access it:

```
You: "Push all context changes to the remote"
Agent: [calls context_sync_push]
       Committed and pushed 5 files to remote.
```

Or from the CLI:

```bash
context-teleport sync push
```

!!! info "What gets pushed"
    Sync push commits all changes in the `.context-teleport/` directory and pushes to the configured remote. If no remote is configured, it still commits locally. Private and ephemeral scoped entries are excluded from the push -- only public entries are shared with the team.


## 7. Second person joins

A teammate clones the project and registers their agent tool. That is all they need to do:

```bash
git clone git@github.com:team/my-project.git
cd my-project
context-teleport register claude-code
```

When they open their agent tool, Context Teleport auto-onboards them with the full project context:

```
Agent: Context Teleport is active for project 'my-project'.
       Knowledge base (3 entries): architecture, tech-stack, deployment.
       Architectural decisions: 2 recorded.
       Agent skills (1 available): deploy-staging.
       Use context_onboarding prompt for full project context.
```

The agent now has access to everything -- architecture, tech stack, deployment process, decisions, and skills -- without anyone needing to explain it manually.

!!! tip "Importing existing context"
    If the new team member was previously using a different agent tool, they can import their existing context first:

    ```bash
    context-teleport import cursor     # imports from .cursor/rules/
    context-teleport import claude-code # imports from CLAUDE.md, MEMORY.md
    ```

    This merges their tool-specific context into the shared store.


## 8. The sync cycle

As the team works, context evolves. The sync cycle is the same as working with code: pull before making changes, push when done.

### Pulling changes

```
You: "Pull the latest context"
Agent: [calls context_sync_pull]
       Pulled 3 changes. No conflicts.
```

### Pushing changes

```
You: "Push our new API design knowledge"
Agent: [calls context_sync_push]
       Committed and pushed 1 file.
```

### From the CLI

```bash
context-teleport sync pull
context-teleport sync push -m "Add API versioning decision"
```

Sync uses standard git operations under the hood. If you look at the git log, you will see commits for each push with auto-generated or custom messages.


## 9. Handling conflicts

When two people modify the same context entry simultaneously, a merge conflict occurs. Context Teleport handles this in several ways, depending on severity.

### Automatic resolution

For markdown files, Context Teleport performs **section-level merge** -- a 3-way merge at `## ` header granularity. If two people edited different sections of the same knowledge entry, the merge resolves automatically with no conflict.

### Manual resolution

When changes overlap in the same section, the pull reports a conflict. You have three strategies:

| Strategy | Behavior |
|----------|----------|
| `ours` (default) | Keep your version, discard theirs |
| `theirs` | Keep their version, discard yours |
| `agent` | Let the agent inspect and resolve each conflict interactively |

The agent strategy is the most powerful -- it lets the agent examine both versions, understand the differences, and produce a merged result:

```
You: "Pull with conflict resolution"
Agent: [calls context_sync_pull with strategy="agent"]
       Conflict detected in knowledge/architecture.md.

       [calls context_conflict_detail to examine both versions]
       The 'ours' version adds a caching layer section.
       The 'theirs' version updates the database section.
       These are in different sections -- I can merge them.

       [calls context_resolve_conflict with merged content]
       [calls context_merge_finalize]
       Merge complete. All conflicts resolved.
```

!!! warning "Conflict state persists"
    When using the `agent` strategy, conflict state is saved to disk between MCP calls. This means you can examine conflicts across multiple messages. Call `context_merge_finalize` when all conflicts are resolved, or `context_merge_abort` to discard the merge and try again.

For a detailed walkthrough of all conflict resolution workflows, see the [Conflict Resolution guide](../guides/conflict-resolution.md).


## 10. Checking project status

At any point, you can get an overview of the store:

```bash
context-teleport status
```

```
╭─ Context Teleport ─╮
│ my-project          │
╰─────────────────────╯
  Schema version: 0.4.0
  Store: /home/user/my-project/.context-teleport
  Knowledge entries: 3
    Keys: architecture, tech-stack, deployment
  Decisions: 2
  Skills: 1
    Names: deploy-staging
```


## Recap

Here is what we covered:

| Step | Command | What it does |
|------|---------|-------------|
| Init | `context-teleport init --name my-project --repo-url ...` | Create store with remote |
| Register | `context-teleport register claude-code` | Configure MCP server for your tool |
| Add knowledge | Agent calls `context_add_knowledge` | Store freeform project knowledge |
| Record decisions | Agent calls `context_record_decision` | ADR-style decision records |
| Create skills | Agent calls `context_add_skill` | Reusable agent capabilities |
| Push | Agent calls `context_sync_push` | Commit and push to remote |
| Join | `git clone` + `context-teleport register` | New member gets auto-onboarded |
| Pull | Agent calls `context_sync_pull` | Fetch team changes |
| Conflicts | `context_sync_pull(strategy="agent")` | Agent-assisted merge resolution |


## Next steps

- **[Team Setup](../guides/team-setup.md)** -- Git remote configuration, branch strategies, and team conventions
- **[Multi-Agent Workflows](../guides/multi-agent.md)** -- Coordinating multiple agents across sessions
- **[Skill Management](../guides/skill-management.md)** -- Usage tracking, feedback, improvement proposals
- **[Context Scoping](../guides/context-scoping.md)** -- Public, private, and ephemeral context boundaries
- **[Adapter Workflows](../guides/adapter-workflows.md)** -- Import and export between agent tools
