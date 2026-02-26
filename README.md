# Context Teleport

![Schema v0.4.0](https://img.shields.io/badge/schema-v0.4.0-blue)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License AGPL-3.0](https://img.shields.io/badge/license-AGPL--3.0-green)
![CI](https://github.com/Mauricio-xx/context-teleport/actions/workflows/ci.yml/badge.svg)

Portable, git-backed context store for AI coding agents.

---

## The problem

AI coding agents accumulate deep context over sessions -- architecture decisions, codebase knowledge, workflow preferences. That context is trapped in tool-specific formats on a single machine. There is no standard way to move it between devices, share it across a team, or use it with a different agent tool.

## What it does

- **[Portable context bundle](https://mauricio-xx.github.io/context-teleport/reference/bundle-format/)** -- knowledge, decisions, skills, state, preferences, session history
- **[Git-backed sync](https://mauricio-xx.github.io/context-teleport/architecture/sync-engine/)** -- push/pull with section-level merge for multi-agent workflows
- **[Cross-tool adapters](https://mauricio-xx.github.io/context-teleport/reference/adapter-protocol/)** -- import/export between Claude Code, OpenCode, Codex, Gemini, and Cursor
- **[Agent skills](https://mauricio-xx.github.io/context-teleport/guides/skill-management/)** -- shareable SKILL.md with usage tracking, feedback, and auto-improvement
- **[MCP server](https://mauricio-xx.github.io/context-teleport/reference/mcp-tools/)** -- 23 tools, 13 resources, 4 prompts for any MCP-compatible agent
- **[Context scoping](https://mauricio-xx.github.io/context-teleport/guides/context-scoping/)** -- public, private, and ephemeral boundaries
- **[LLM conflict resolution](https://mauricio-xx.github.io/context-teleport/guides/conflict-resolution/)** -- agents inspect and resolve merge conflicts via MCP tools
- **[EDA domain support](https://mauricio-xx.github.io/context-teleport/guides/eda-workflows/)** -- parsers for LibreLane, OpenROAD, Magic DRC, Netgen LVS, Liberty
- **[GitHub issue bridge](https://mauricio-xx.github.io/context-teleport/guides/github-issues/)** -- import issues as knowledge or decisions via `gh` CLI

## Quickstart

```bash
# Initialize a context store
uvx context-teleport init --name my-project

# Register your agent tool
uvx context-teleport register claude-code

# Start working -- the agent manages context from here
```

```
You: "Save that we're using hexagonal architecture with FastAPI"
Agent: [calls context_add_knowledge] Done.

You: "Record the decision to use PostgreSQL"
Agent: [calls context_record_decision] Decision recorded.

You: "Sync with the team"
Agent: [calls context_sync_push] Pushed 2 changes.
```

## Documentation

Full documentation at **[mauricio-xx.github.io/context-teleport](https://mauricio-xx.github.io/context-teleport/)**.

- [Getting Started](https://mauricio-xx.github.io/context-teleport/getting-started/) -- installation, quickstart, first project tutorial
- [Guides](https://mauricio-xx.github.io/context-teleport/guides/) -- team setup, multi-agent workflows, conflict resolution, EDA integration
- [Reference](https://mauricio-xx.github.io/context-teleport/reference/) -- CLI, MCP tools/resources/prompts, schema, adapters
- [Architecture](https://mauricio-xx.github.io/context-teleport/architecture/) -- system design with TikZ diagrams
- [Examples](https://mauricio-xx.github.io/context-teleport/examples/) -- solo developer, multi-agent team, EDA project

## Supported tools

| Tool | Import | Export | MCP Registration | Skills |
|------|--------|--------|-----------------|--------|
| Claude Code | Yes | Yes | `.claude/mcp.json` | Yes |
| OpenCode | Yes | Yes | `opencode.json` | Yes |
| Codex | Yes | Yes | -- | Yes |
| Gemini | Yes | Yes | `.gemini/settings.json` | Yes |
| Cursor | Yes | Yes | `.cursor/mcp.json` | Yes |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, or the [full contributing guide](https://mauricio-xx.github.io/context-teleport/contributing/) for testing, adding adapters, and adding EDA parsers.

All contributions require signing the [CLA](CLA.md).

## License

AGPL-3.0-or-later.
