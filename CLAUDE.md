# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Context Teleport** is a research/design project exploring portable state for AI coding agent sessions. The core problem: when an AI coding agent (Claude Code, Cursor, Copilot, etc.) accumulates deep context over multiple sessions, that context is trapped on the local machine with no standard mechanism to move, share, fork, or merge it.

The goal is a general-purpose solution for multi-device and multi-user workflows: teams/organizations where each member works on different machines and setups, and agent context needs to flow seamlessly across all of them.

## Key Documents

- `BRIEF` -- Problem statement, landscape analysis, strategic positioning, proposed architecture, and next steps
- `Agent Context Portability_ A New Frontier.md` -- Extended research document covering paradigms (relational DB memory, git-backed context repos, dual-layer workspace sync, semantic spec anchoring), the proposed Context Bundle schema, and standardization layers (MCP, AAIF/AGENTS.md)

## Core Concepts

- **Context Bundle**: Portable, serializable package of agent context (knowledge, state, preferences, history)
- **Context Merge**: Git-like merge for agent knowledge from diverged sessions
- **Context Scope**: Public (team), private (user), ephemeral (session-only)
- **Context Schema**: Standard format readable/writable by multiple agent tools

## Landscape Summary (Feb 2026)

Research completed. Key findings:

- **No standard exists** for agent context portability across tools or team members
- **GitHub Copilot** is most advanced (cross-agent memory, Spaces) but locked to GitHub ecosystem
- **Claude Enterprise** has team memory on claude.ai but it is completely disconnected from Claude Code
- **Emerging MCP memory servers** (OpenMemory, Engram, EchoVault) solve individual persistence but not team sync or cross-tool portability
- **AGENTS.md** (AAIF standard) covers static instructions; dynamic/learned context has no equivalent standard
- **Highest-value gap**: team context synchronization (N people, N machines, N agents with merge capability)

## Strategic Decisions

- Complement AGENTS.md (static instructions) with dynamic/learned context -- don't compete
- Expose as MCP server for cross-tool compatibility (Claude Code, OpenCode, Continue, Cursor)
- Target Claude Code first, design adapters for other tools without architecture changes
- Focus on team-level context sharing over individual persistence (already partially solved by others)

## Proposed Bundle Structure

```
context-bundle/
  manifest.json
  knowledge/        # architecture, decisions (ADR-style), known issues
  state/            # session progress, roadmap
  preferences/      # interaction style, workflow config
  history/          # compressed session summaries (ndjson)
```

## Project Phase

Core implementation complete. 150 tests passing. Ready for integration testing.

- [x] Landscape survey of commercial and open-source tools
- [x] Research on emerging memory/portability tools and standards
- [x] Define prototype scope and target use cases
- [x] Design minimal context bundle schema
- [x] Build Claude Code adapter (import/export + MCP registration)
- [x] Implement MCP server (10 tools, 8 resources, 3 prompts)
- [x] Bundle versioning / migration framework
- [x] Merge conflict detection and resolution UX

## Development Notes

- Python 3.11+, venv, hatchling build system
- `pytest tests/ -v` to run full suite (150 tests)
- `ruff check src/ tests/` for linting
- `pip install -e ".[dev]"` to install with dev deps
- MCP server: `ctx-mcp` entry point (stdio transport)
- Register with Claude Code: `ctx register`
