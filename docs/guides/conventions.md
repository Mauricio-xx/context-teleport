# Team Conventions

Team conventions are shared behavioral rules that define how agents should work in your
project. They are distinct from knowledge ("how to behave" vs "what we know") and have
higher priority -- conventions appear before knowledge in onboarding and instructions.

## When to use conventions

- Git workflow rules (branching strategy, commit messages, no force-push)
- Environment constraints (no sudo, use venvs, Docker for isolation)
- Communication style (language, tone, formatting preferences)
- Naming standards (API field casing, file naming, variable conventions)
- Security policies (no secrets in code, credential handling)

## Adding conventions

### Via agent

```
You: "We always use feature branches and never force-push to main. Save that as a convention."
Agent: [calls context_add_convention with key="git"] Done.
```

### Via CLI

```bash
# Inline content
context-teleport convention add git "Always use feature branches. Never force-push to main."

# From a file
context-teleport convention add git --file git-rules.md

# From stdin
echo "No sudo. Use venvs." | context-teleport convention add environment
```

### Import from an existing file

If you already have rules in a CLAUDE.md, AGENTS.md, or similar file:

```bash
context-teleport import conventions ~/.claude/CLAUDE.md
```

The importer splits the file by `## ` headers. Each section becomes a separate
convention with the slugified header as the key. For example:

```markdown
# My Team Rules

## Git Workflow
Always use feature branches.
Commit early, commit often.

## Environment
No sudo access.
Use virtual environments for Python.
```

This produces two conventions: `git-workflow` and `environment`.

## Managing conventions

```bash
# List all conventions
context-teleport convention list

# Read a specific convention
context-teleport convention get git

# Update a convention
context-teleport convention add git "Updated content here."

# Remove a convention
context-teleport convention rm git

# Change scope
context-teleport convention scope git private
```

## How conventions reach agents

Conventions are delivered to agents through multiple channels:

1. **MCP instructions** -- listed before knowledge at session start
2. **Onboarding prompt** -- included in the `## Team Conventions` section
3. **Adapter export** -- written to each tool's native format

### Export formats

| Adapter | Format |
|---------|--------|
| Claude Code | `### Team Conventions` section in CLAUDE.md managed block |
| Cursor | `.cursor/rules/ctx-convention-{key}.mdc` with `alwaysApply: True` |
| Gemini | `.gemini/rules/ctx-convention-{key}.md` |
| OpenCode | `### convention: {key}` entries in AGENTS.md managed section |
| Codex | `### convention: {key}` entries in AGENTS.md managed section |

## Conventions vs knowledge

| Aspect | Conventions | Knowledge |
|--------|------------|-----------|
| Purpose | How agents should behave | What the project is about |
| Priority | Higher (listed first in onboarding) | Lower |
| Storage | `conventions/<key>.md` | `knowledge/<key>.md` |
| Typical content | Rules, policies, constraints | Architecture, tech stack, API docs |

## Scoping

Conventions support the same scoping as other content types:

- **public** (default): shared with the team via git
- **private**: local to this machine, not synced
- **ephemeral**: session-only, cleared on ephemeral cleanup
