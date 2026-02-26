# Getting Started

Get Context Teleport running in your project in under 5 minutes.

## Path to first use

1. **[Installation](installation.md)** -- Install via `uvx` (recommended), `pip`, or from source
2. **[Quickstart](quickstart.md)** -- Initialize a store, register your agent tool, and start a session
3. **[First Project](first-project.md)** -- Extended tutorial: full lifecycle from init to team sync

## Prerequisites

- Python 3.11+
- Git
- An MCP-compatible agent tool (Claude Code, OpenCode, Cursor, or Gemini)

## Fastest path

If you just want to try it right now:

```bash
uvx context-teleport init --name my-project
uvx context-teleport register claude-code
```

Then open Claude Code and start talking. The agent has full access to the context store.
