# CLI Reference

The entry point for all commands is `context-teleport`. It operates as a single smart
dispatch: when invoked in a TTY with arguments it runs the CLI, when invoked
non-interactively with no arguments it starts the MCP server.

All commands accept `--format json` (short: `-F json`) for machine-readable output.

---

## Global Options

| Option | Short | Description |
|---|---|---|
| `--format` | `-F` | Output format: `json` or `text` (default: `text`) |
| `--help` | | Show help for any command |

---

## Top-Level Commands

### init

Initialize a context store in the current project directory.

```bash
context-teleport init [--name PROJECT_NAME] [--repo-url URL]
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--name` | `-n` | directory name | Project name |
| `--repo-url` | | `""` | Git remote URL |

Creates the `.context-teleport/` directory with `manifest.json`, `knowledge/`,
`knowledge/decisions/`, `skills/`, and supporting files.

!!! tip
    If the project root contains EDA markers (LibreLane config, Makefile with
    OpenROAD, Liberty files), `init` will print detected EDA project information.

---

### status

Show store state, sync status, and adapter info.

```bash
context-teleport status
```

Displays project name, schema version, knowledge count, decision count, skill count,
current task, blockers, and enabled adapters. Also runs EDA project detection if
markers are present.

---

### get

Read any value by dotpath. Outputs JSON by default (designed for agent use).

```bash
context-teleport get <dotpath>
```

| Argument | Description |
|---|---|
| `dotpath` | Path using dot notation (e.g. `knowledge.architecture`, `state.current_task`) |

```bash
# Read a knowledge entry
context-teleport get knowledge.architecture

# Read the current task
context-teleport get state.current_task
```

---

### set

Write any value by dotpath. Outputs JSON by default.

```bash
context-teleport set <dotpath> <value>
```

| Argument | Description |
|---|---|
| `dotpath` | Path using dot notation |
| `value` | Value to set |

```bash
context-teleport set knowledge.stack "Python 3.12, FastAPI"
context-teleport set state.current_task "Implement auth module"
```

---

### search

Full-text search across all context.

```bash
context-teleport search <query> [--json]
```

| Argument / Option | Description |
|---|---|
| `query` | Search query string |
| `--json` | Force JSON output (alternative to `--format json`) |

Returns matching lines with key, line number, match text, and relevance score.

---

### summary

One-page context summary optimized for LLM context windows. Includes knowledge entries,
decisions, current state, and recent sessions.

```bash
context-teleport summary
```

---

### push

Stage context changes, commit, and push to remote. Top-level shortcut for `sync push`.

```bash
context-teleport push [-m MESSAGE]
```

| Option | Short | Description |
|---|---|---|
| `--message` | `-m` | Commit message (auto-generated if omitted) |

If no remote is configured, the command commits locally and reports
`status: committed`.

---

### pull

Pull remote context and merge. Top-level shortcut for `sync pull`.

```bash
context-teleport pull [-s STRATEGY]
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--strategy` | `-s` | `ours` (or config value) | Merge strategy: `ours`, `theirs`, `interactive`, `agent` |

When using `interactive` strategy, the CLI walks through each conflict in a TUI.
Falls back to `ours` in non-interactive (piped) mode.

!!! tip
    Set a default strategy with `context-teleport config set default_strategy theirs`
    to avoid passing `-s` every time.

---

### diff

Show context changes. Top-level shortcut for `sync diff`.

```bash
context-teleport diff [--remote]
```

| Option | Description |
|---|---|
| `--remote` | Compare local context with remote |

---

### log

Show context commit history. Top-level shortcut for `sync log`.

```bash
context-teleport log [--oneline] [-n COUNT]
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--oneline` | | `false` | One-line format |
| `-n` | | `10` | Number of entries to show |

---

### register

Register the Context Teleport MCP server with one or more AI coding tools. Auto-detects
installed tools when no tool is specified.

```bash
context-teleport register [TOOL] [--local]
```

| Argument / Option | Description |
|---|---|
| `TOOL` | Tool name: `claude-code`, `opencode`, `codex`, `gemini`, `cursor`. Omit to auto-detect. |
| `--local` | Use local `context-teleport` command instead of `uvx` (for development installs) |

```bash
# Auto-detect and register all available tools
context-teleport register

# Register for a specific tool
context-teleport register claude-code

# Use local install instead of uvx
context-teleport register --local
```

---

### unregister

Remove MCP server registration from one or all detected tools.

```bash
context-teleport unregister [TOOL]
```

| Argument | Description |
|---|---|
| `TOOL` | Tool name. Omit to unregister from all detected tools. |

---

### watch

Monitor the context store for file changes and auto-commit/push via git.
Uses `watchdog` for filesystem events if installed, falls back to polling.
Press `Ctrl+C` to stop (performs a final sync before exiting).

```bash
context-teleport watch [--debounce SECONDS] [--interval SECONDS] [--no-push]
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--debounce` | `-d` | `5.0` | Seconds to wait after last change before syncing |
| `--interval` | `-i` | `2.0` | Polling interval in seconds (polling mode only) |
| `--no-push` | | `false` | Only commit locally, do not push to remote |

---

## Subcommand Groups

### knowledge

Manage knowledge entries. Prefix: `context-teleport knowledge`.

#### list

```bash
context-teleport knowledge list [--scope public|private|ephemeral]
```

| Option | Short | Description |
|---|---|---|
| `--scope` | `-s` | Filter by scope |

#### get

```bash
context-teleport knowledge get <key>
```

| Argument | Description |
|---|---|
| `key` | Knowledge entry key |

#### set

```bash
context-teleport knowledge set <key> [content] [--file PATH] [--scope SCOPE]
```

| Argument / Option | Short | Description |
|---|---|---|
| `key` | | Knowledge entry key |
| `content` | | Content string (reads stdin if omitted and no `--file`) |
| `--file` | `-f` | Read content from file |
| `--scope` | `-s` | Scope: `public`, `private`, `ephemeral` |

#### rm

```bash
context-teleport knowledge rm <key>
```

#### scope

```bash
context-teleport knowledge scope <key> <scope>
```

| Argument | Description |
|---|---|
| `key` | Knowledge entry key |
| `scope` | New scope: `public`, `private`, `ephemeral` |

#### search

```bash
context-teleport knowledge search <query>
```

Full-text search within knowledge files only. Returns key, line number, and matched text.

---

### decision

Manage decision records (Architecture Decision Records). Prefix: `context-teleport decision`.

#### list

```bash
context-teleport decision list [--scope public|private|ephemeral]
```

| Option | Short | Description |
|---|---|---|
| `--scope` | `-s` | Filter by scope |

#### get

```bash
context-teleport decision get <id_or_title>
```

| Argument | Description |
|---|---|
| `id_or_title` | Decision ID (integer) or title string for fuzzy match |

#### add

```bash
context-teleport decision add <title> [--file PATH] [--scope SCOPE]
```

| Argument / Option | Short | Description |
|---|---|---|
| `title` | | Decision title |
| `--file` | `-f` | Read ADR content from a markdown file |
| `--scope` | `-s` | Scope: `public`, `private`, `ephemeral` |

When neither `--file` nor stdin is provided, opens `$EDITOR` (default: `vi`) with a
markdown template containing Context, Decision, and Consequences sections.

---

### skill

Manage agent skills (SKILL.md files). Prefix: `context-teleport skill`.

#### list

```bash
context-teleport skill list [--scope public|private|ephemeral]
```

| Option | Short | Description |
|---|---|---|
| `--scope` | `-s` | Filter by scope |

#### get

```bash
context-teleport skill get <name>
```

Prints the full SKILL.md content (YAML frontmatter + markdown body).

#### add

```bash
context-teleport skill add <name> [--file PATH] [--description TEXT] [--scope SCOPE]
```

| Argument / Option | Short | Description |
|---|---|---|
| `name` | | Skill name (used as directory name under `skills/`) |
| `--file` | `-f` | Read SKILL.md content from file |
| `--description` | `-d` | Skill description (used in auto-generated frontmatter) |
| `--scope` | `-s` | Scope: `public`, `private`, `ephemeral` |

When no file or stdin is provided, generates a template with YAML frontmatter.

#### rm

```bash
context-teleport skill rm <name>
```

#### scope

```bash
context-teleport skill scope <name> <scope>
```

| Argument | Description |
|---|---|
| `name` | Skill name |
| `scope` | New scope: `public`, `private`, `ephemeral` |

#### stats

Show usage and feedback statistics for all skills.

```bash
context-teleport skill stats [--sort usage|rating|name]
```

| Option | Default | Description |
|---|---|---|
| `--sort` | `name` | Sort order: `usage`, `rating`, `name` |

Displays a table with columns: name, usage count, average rating, rating count,
last used date, and attention flag (`!` if the skill needs review).

#### feedback

List feedback entries for a specific skill.

```bash
context-teleport skill feedback <name>
```

Displays agent, rating (1-5), comment, and timestamp for each feedback entry.

#### review

Show skills needing attention (average rating below 3.0 with 2 or more ratings).

```bash
context-teleport skill review
```

For each flagged skill, shows average rating, rating count, usage count, and the
three most recent feedback entries.

#### proposals

List skill improvement proposals.

```bash
context-teleport skill proposals [--skill NAME] [--status STATUS]
```

| Option | Description |
|---|---|
| `--skill` | Filter by skill name |
| `--status` | Filter by status: `pending`, `accepted`, `rejected`, `upstream` |

#### apply-proposal

Accept or reject a skill improvement proposal.

```bash
context-teleport skill apply-proposal <skill> <id> [--reject]
```

| Argument / Option | Description |
|---|---|
| `skill` | Skill name |
| `id` | Proposal ID (full UUID or unambiguous prefix) |
| `--reject` | Reject instead of accept |

When accepted, the proposal content replaces the current SKILL.md.

#### propose-upstream

Push an accepted proposal as a pull request to an upstream skills pack repository.

```bash
context-teleport skill propose-upstream <skill> <id> --repo OWNER/REPO
```

| Argument / Option | Description |
|---|---|
| `skill` | Skill name |
| `id` | Proposal ID (full UUID or unambiguous prefix) |
| `--repo` | Target repository in `OWNER/REPO` format (required) |

Clones the target repo, creates a branch (`skill-improve/<name>-<short_id>`),
writes the proposed SKILL.md, commits, pushes, and opens a PR via `gh pr create`.
Updates the proposal status to `upstream` on success.

!!! tip
    Requires `gh` CLI to be installed and authenticated.

---

### state

Manage ephemeral session state. Prefix: `context-teleport state`.

#### show

```bash
context-teleport state show
```

Displays current task, blockers, progress, last agent, last machine, and update timestamp.

#### set

```bash
context-teleport state set <key> <value>
```

| Argument | Description |
|---|---|
| `key` | State field: `current_task`, `blockers` (comma-separated), `last_agent`, `last_machine`, or any custom key (stored in `progress` dict) |
| `value` | Value to set |

#### clear

```bash
context-teleport state clear
```

Resets all ephemeral session state to defaults.

---

### sync

Git-backed sync commands. Prefix: `context-teleport sync`. These are also available as
top-level shortcuts (`push`, `pull`, `diff`, `log`).

#### push

```bash
context-teleport sync push [-m MESSAGE]
```

Stage context changes in `.context-teleport/`, commit, and push.

#### pull

```bash
context-teleport sync pull [-s STRATEGY]
```

Pull remote context and merge. Uses section-level merge for markdown files
before falling back to the chosen strategy.

| Option | Short | Default | Description |
|---|---|---|---|
| `--strategy` | `-s` | `ours` (or config) | `ours`, `theirs`, `interactive`, `agent` |

#### resolve

```bash
context-teleport sync resolve [-s STRATEGY]
```

Retry merge resolution for pending conflicts. Only supports `ours` and `theirs`.

| Option | Short | Default | Description |
|---|---|---|---|
| `--strategy` | `-s` | `ours` | `ours` or `theirs` |

!!! tip
    For interactive resolution, use `context-teleport pull --strategy interactive`
    instead. The `resolve` command is for automated conflict resolution.

#### diff

```bash
context-teleport sync diff [--remote]
```

#### log

```bash
context-teleport sync log [--oneline] [-n COUNT]
```

---

### import

Import context from external tools, bundles, EDA artifacts, or GitHub issues.
Prefix: `context-teleport import`.

All import commands support `--dry-run` to preview what would be imported.

#### Adapter Import

```bash
context-teleport import claude-code [--dry-run]
context-teleport import opencode [--dry-run]
context-teleport import codex [--dry-run]
context-teleport import gemini [--dry-run]
context-teleport import cursor [--dry-run]
```

Each adapter imports tool-specific files into the context store:

| Tool | Sources |
|---|---|
| `claude-code` | `MEMORY.md`, `CLAUDE.md`, `.claude/skills/*/SKILL.md` |
| `opencode` | `AGENTS.md`, SQLite sessions, `.opencode/skills/*/SKILL.md` |
| `codex` | `AGENTS.md`, `.codex/instructions.md`, `.codex/skills/*/SKILL.md` |
| `gemini` | `.gemini/rules/*.md`, `STYLEGUIDE.md`, `GEMINI.md`, `.gemini/skills/*/SKILL.md` |
| `cursor` | `.cursor/rules/*.mdc`, `.cursorrules`, `.cursor/skills/*/SKILL.md` |

#### Bundle Import

```bash
context-teleport import bundle <path>
```

Import a portable `.ctxbundle` archive.

#### EDA Import

```bash
context-teleport import eda <path> [--type TYPE] [--dry-run]
```

| Option | Short | Description |
|---|---|---|
| `--type` | `-t` | Force importer type. Auto-detected if omitted. |
| `--dry-run` | | Preview what would be imported |

Available importer types: `librelane-config`, `librelane-metrics`, `magic-drc`,
`netgen-lvs`, `orfs-config`, `liberty`.

#### GitHub Import

```bash
context-teleport import github [OPTIONS]
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--repo` | `-r` | auto-detect | GitHub repository (`owner/repo`) |
| `--issue` | `-i` | | Import a single issue by number |
| `--labels` | `-l` | | Comma-separated label filter |
| `--state` | `-s` | `all` | Issue state: `open`, `closed`, `all` |
| `--since` | | | Only issues after this date (ISO format, e.g. `2025-01-01`) |
| `--limit` | `-n` | `50` | Maximum issues to fetch |
| `--as-decisions` | | `false` | Also create decision records for closed issues |
| `--dry-run` | | `false` | Preview what would be imported |

!!! tip
    Requires `gh` CLI to be installed and authenticated. Repository is auto-detected
    from `git remote -v` when `--repo` is omitted.

---

### export

Export context to external tool locations or bundles.
Prefix: `context-teleport export`.

All export commands support `--dry-run` to preview what would be exported.

#### Adapter Export

```bash
context-teleport export claude-code [--dry-run]
context-teleport export opencode [--dry-run]
context-teleport export codex [--dry-run]
context-teleport export gemini [--dry-run]
context-teleport export cursor [--dry-run]
```

#### Bundle Export

```bash
context-teleport export bundle <path>
```

Export the context store as a portable `.ctxbundle` archive.

---

### config

Manage global configuration. Prefix: `context-teleport config`.

#### get

```bash
context-teleport config get <key>
```

#### set

```bash
context-teleport config set <key> <value>
```

#### list

```bash
context-teleport config list
```

Available configuration keys:

| Key | Valid Values | Description |
|---|---|---|
| `default_strategy` | `ours`, `theirs`, `interactive`, `agent` | Default merge strategy for `pull` |
| `default_scope` | `public`, `private`, `ephemeral` | Default scope for new entries |
