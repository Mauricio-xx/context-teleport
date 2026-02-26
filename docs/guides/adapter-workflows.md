# Adapter Workflows

This guide covers importing context from existing AI coding tools into Context Teleport
and exporting it back out to other tools. Use these workflows for tool migration,
multi-tool setups, and portable context bundles.

## Supported adapters

| Adapter     | Import sources                                          | Export targets                     | MCP registration |
|-------------|---------------------------------------------------------|------------------------------------|------------------|
| Claude Code | MEMORY.md, CLAUDE.md, `.claude/skills/*/SKILL.md`      | MEMORY.md, `.claude/skills/`       | `.claude/mcp.json` |
| Cursor      | `.cursor/rules/*.mdc`, `.cursorrules`, `.cursor/skills/` | `.cursor/rules/`, `.cursor/skills/` | `.cursor/mcp.json` |
| OpenCode    | AGENTS.md, SQLite sessions, `opencode/skills/`          | AGENTS.md, `opencode/skills/`      | `opencode.json`    |
| Codex       | AGENTS.md, `.codex/instructions.md`, `codex/skills/`    | AGENTS.md, `.codex/skills/`        | Not supported      |
| Gemini      | `.gemini/rules/*.md`, STYLEGUIDE.md, GEMINI.md, `.gemini/skills/` | `.gemini/rules/`, `.gemini/skills/` | `.gemini/settings.json` |

## Importing context

### From a single tool

```bash
context-teleport import claude-code
```

This reads Claude Code's native files (MEMORY.md, CLAUDE.md, any skills in
`.claude/skills/`) and writes them into the `.context-teleport/` store as knowledge
entries and skills.

The same pattern works for every adapter:

```bash
context-teleport import cursor
context-teleport import opencode
context-teleport import codex
context-teleport import gemini
```

### Dry-run preview

Before importing, preview what would change:

```bash
context-teleport import claude-code --dry-run
```

Output:

```
Dry run -- the following would be imported:
  knowledge: claude-memory (MEMORY.md)
  knowledge: claude-instructions (CLAUDE.md)
  skill: deploy-staging (.claude/skills/deploy-staging/SKILL.md)
  skill: code-review (.claude/skills/code-review/SKILL.md)
```

No files are written during a dry run. Use it to verify before committing to an import.

### What gets imported per tool

**Claude Code:**
- `MEMORY.md` -> knowledge entry `claude-memory`
- `CLAUDE.md` -> knowledge entry `claude-instructions`
- `.claude/skills/*/SKILL.md` -> skills with matching names

**Cursor:**
- `.cursor/rules/*.mdc` -> knowledge entries (one per rule file)
- `.cursorrules` -> knowledge entry `cursorrules`
- `.cursor/skills/*/SKILL.md` -> skills

**OpenCode:**
- `AGENTS.md` -> knowledge entry `agents-md`
- SQLite session database -> session entries
- `opencode/skills/*/SKILL.md` -> skills

**Codex:**
- `AGENTS.md` -> knowledge entry `agents-md`
- `.codex/instructions.md` -> knowledge entry `codex-instructions`
- `codex/skills/*/SKILL.md` -> skills

**Gemini:**
- `.gemini/rules/*.md` -> knowledge entries (one per rule file)
- `STYLEGUIDE.md` -> knowledge entry `styleguide`
- `GEMINI.md` -> knowledge entry `gemini-instructions`
- `.gemini/skills/*/SKILL.md` -> skills

## Exporting context

Export pushes the store content into a tool's native file format:

```bash
context-teleport export cursor
```

This writes knowledge entries into `.cursor/rules/` as `.mdc` files and skills into
`.cursor/skills/*/SKILL.md`.

### Managed sections

When exporting to files that may contain user content (like AGENTS.md or MEMORY.md),
Context Teleport uses managed section markers to avoid overwriting manual edits:

```markdown
# My Project Notes

Some hand-written notes here...

<!-- ctx:start -->
## Project Knowledge (managed by Context Teleport)

- API uses snake_case for JSON fields
- PostgreSQL for user service
<!-- ctx:end -->

More hand-written notes below...
```

Everything between `<!-- ctx:start -->` and `<!-- ctx:end -->` is managed by Context
Teleport. Content outside those markers is preserved during export. Re-exporting
updates only the managed section.

### Dry-run for exports

```bash
context-teleport export cursor --dry-run
```

Output:

```
Dry run -- the following would be exported:
  .cursor/rules/api-conventions.mdc: Knowledge entry
  .cursor/rules/deployment-guide.mdc: Knowledge entry
  .cursor/skills/deploy-staging/SKILL.md: Skill
```

## Tool migration

Moving from one AI coding tool to another is a two-step process:

```bash
# Step 1: Import from old tool
context-teleport import claude-code

# Step 2: Export to new tool
context-teleport export cursor
```

The context store acts as the intermediary format. You can also register the new tool's
MCP server so it gets live context going forward:

```bash
context-teleport register cursor
```

### Full migration example: Claude Code to Cursor

```bash
# Import existing Claude Code context
context-teleport import claude-code
# Verify what was imported
context-teleport status
# Export to Cursor's format
context-teleport export cursor
# Register MCP for live context
context-teleport register cursor
# Optionally unregister old tool
context-teleport unregister claude-code
```

After this, Cursor has all the knowledge and skills that Claude Code accumulated, and
the MCP server provides live context going forward.

## Skills as a cross-tool standard

Skills use the same `SKILL.md` format across all adapters. A skill directory looks
like this:

```
skills/
  deploy-staging/
    SKILL.md
```

The `SKILL.md` file contains YAML frontmatter and a markdown body:

```markdown
---
name: deploy-staging
description: Deploy the application to the staging environment
---

## Steps

1. Run the test suite: `pytest tests/ -v`
2. Build the Docker image: `docker build -t app:staging .`
3. Push to registry: `docker push registry.example.com/app:staging`
4. Deploy via kubectl: `kubectl apply -f k8s/staging/`

## Verification

- Check pod status: `kubectl get pods -n staging`
- Hit the health endpoint: `curl https://staging.example.com/health`
```

When importing from Claude Code, skills in `.claude/skills/*/SKILL.md` are read
directly. When exporting to Cursor, they are written to `.cursor/skills/*/SKILL.md`.
The format is identical -- only the directory path changes.

## Bundle import/export

Bundles are portable `.ctxbundle` archives that package the entire context store for
transfer outside of git:

```bash
# Export to a bundle file
context-teleport export bundle ./project-context.ctxbundle

# Import from a bundle file
context-teleport import bundle ./project-context.ctxbundle
```

Use bundles when:

- Sharing context with someone who does not have access to the git remote
- Backing up context before a major refactor
- Transferring context between unrelated projects
- Onboarding a contractor or external collaborator

> **Note:** Bundles include only `public`-scoped entries. Private and ephemeral entries
> are excluded.

## JSON output

All import and export commands support `--format json` for scripting:

```bash
context-teleport import claude-code --format json
```

```json
{
  "imported": 4,
  "items": [
    {"type": "knowledge", "key": "claude-memory", "source": "MEMORY.md"},
    {"type": "knowledge", "key": "claude-instructions", "source": "CLAUDE.md"},
    {"type": "skill", "key": "deploy-staging", "source": ".claude/skills/deploy-staging/SKILL.md"},
    {"type": "skill", "key": "code-review", "source": ".claude/skills/code-review/SKILL.md"}
  ]
}
```

## Additional import sources

Beyond tool adapters, Context Teleport supports importing from other sources:

- **EDA artifacts:** `context-teleport import eda <path>` -- parses LibreLane configs,
  DRC reports, LVS results, Liberty files, and more. See the EDA documentation for
  details.

- **GitHub issues:** `context-teleport import github --repo owner/repo` -- imports
  issues as knowledge entries (and optionally as decisions for closed issues). Requires
  the `gh` CLI.
