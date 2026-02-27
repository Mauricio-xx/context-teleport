# Context Teleport

**Portable, git-backed context store for AI coding agents.**

---

AI coding agents accumulate deep context over sessions -- architecture decisions, codebase knowledge, workflow preferences, task progress. That context is trapped in tool-specific formats on a single machine. There is no standard way to move it between devices, share it across a team, or use it with a different agent tool.

Context Teleport solves this. It provides a structured, git-backed store that any MCP-compatible agent can read and write through natural language. Register once, and your agent manages context autonomously from that point forward.

## Key features

- **Portable context bundle** -- structured store for knowledge, decisions, conventions, skills, state, preferences, and session history
- **Team conventions** -- shared behavioral rules (git workflow, environment, communication) across all tools
- **Git-backed sync** -- push/pull context to any git remote, works like code sync
- **Section-level merge** -- 3-way merge at markdown section granularity, reduces false conflicts
- **Cross-tool adapters** -- import/export between Claude Code, OpenCode, Codex, Gemini, and Cursor
- **Agent skills** -- shareable SKILL.md capabilities with usage tracking, feedback, and auto-improvement
- **MCP server** -- 29 tools, 16 resources, 4 prompts; works with any MCP-compatible agent
- **Auto-initialization** -- MCP server auto-creates the store in any git repo, no explicit init needed
- **Context scoping** -- public (team), private (user-only), ephemeral (session-only) boundaries
- **Agent attribution** -- tracks which agent wrote each entry
- **LLM-based conflict resolution** -- agents can inspect and resolve merge conflicts via MCP tools
- **EDA/PDK domain support** -- artifact parsers for LibreLane, OpenROAD, Magic DRC, Netgen LVS, and Liberty files
- **GitHub issue bridge** -- import issues and decisions from GitHub via `gh` CLI

## Quick overview

```
1. Install            uvx context-teleport --help
2. Initialize         context-teleport init --name my-project
3. Register           context-teleport register claude-code
4. Work normally      Agent reads/writes context via MCP tools
5. Sync               Agent pushes/pulls via git automatically
```

## Documentation

<div class="grid cards" markdown>

- :material-rocket-launch: **[Getting Started](getting-started/index.md)**

    Install, configure, and run your first project in 5 minutes.

- :material-book-open-variant: **[Guides](guides/index.md)**

    Team setup, multi-agent workflows, conflict resolution, EDA integration, and more.

- :material-code-tags: **[Reference](reference/index.md)**

    Complete CLI, MCP tools, resources, prompts, schema, and adapter documentation.

- :material-sitemap: **[Architecture](architecture/index.md)**

    System design, data flow diagrams, and internal component documentation.

- :material-file-document-multiple: **[Examples](examples/index.md)**

    End-to-end walkthroughs for solo developers, teams, and EDA projects.

- :material-account-group: **[Contributing](contributing/index.md)**

    Development setup, testing, and how to add new adapters or parsers.

</div>

## Supported tools

| Tool | Import | Export | MCP Registration | Skills |
|------|--------|--------|-----------------|--------|
| Claude Code | Yes | Yes | `.claude/mcp.json` | Yes |
| OpenCode | Yes | Yes | `opencode.json` | Yes |
| Codex | Yes | Yes | -- | Yes |
| Gemini | Yes | Yes | `.gemini/settings.json` | Yes |
| Cursor | Yes | Yes | `.cursor/mcp.json` | Yes |

## License

[AGPL-3.0-or-later](https://www.gnu.org/licenses/agpl-3.0.html). Contributions require a [CLA](https://github.com/Mauricio-xx/context-teleport/blob/main/CLA.md).
