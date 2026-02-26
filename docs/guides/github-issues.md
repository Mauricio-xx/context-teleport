# GitHub Issues

Context Teleport can import GitHub issues as knowledge entries and, optionally, synthesize closed issues into Architecture Decision Records (ADRs). This is useful for bringing issue discussions, bug reports, and resolved decisions into the context store where AI agents can reference them.

## Prerequisites

The GitHub issue bridge relies on the `gh` CLI tool (GitHub's official command-line interface). It must be installed and authenticated before use.

```bash
# Install gh (if not already available)
# See https://cli.github.com/ for platform-specific instructions

# Authenticate
gh auth login
```

Verify authentication is working:

```bash
gh auth status
```

> **Note:** Context Teleport uses `gh` directly via subprocess rather than a Python GitHub library. This means zero additional dependencies and leverages your existing `gh` authentication.

## Repository Detection

When you omit the `--repo` flag, Context Teleport automatically detects the GitHub repository by parsing `git remote -v` in the current directory. It recognizes both SSH and HTTPS remote URLs:

```bash
# These remotes are auto-detected:
# git@github.com:owner/repo.git
# https://github.com/owner/repo.git

cd /path/to/your-repo
context-teleport import github
# Auto-detected repository: owner/repo
```

If auto-detection fails (e.g., you are outside a git repo, or the remote is not on github.com), specify the repository explicitly:

```bash
context-teleport import github --repo owner/repo
```

## Import Commands

### Import All Open and Closed Issues

```bash
context-teleport import github --repo owner/repo
```

By default, this fetches up to 50 issues in all states (`open`, `closed`).

### Import a Single Issue

```bash
context-teleport import github --issue 835
```

### Filter by Labels

```bash
context-teleport import github --labels bug,critical
```

Multiple labels are comma-separated. Only issues matching **any** of the specified labels are included.

### Filter by State

```bash
context-teleport import github --state open
context-teleport import github --state closed
context-teleport import github --state all       # default
```

### Filter by Date

```bash
context-teleport import github --since 2025-01-01
```

Only issues created after the specified date (ISO format) are fetched.

### Limit Results

```bash
context-teleport import github --limit 100
```

The default limit is 50 issues per import.

### Preview with Dry Run

```bash
context-teleport import github --repo owner/repo --dry-run
```

Shows what would be imported without writing anything to the store.

## Key Naming

Each imported issue produces a knowledge entry with a deterministic key following the pattern:

```
github-issue-<repo-slug>-<number>
```

For example, importing issue #835 from `IHP-GmbH/IHP-Open-PDK` produces:

```
github-issue-ihp-gmbh-ihp-open-pdk-835
```

Re-importing the same issue overwrites the existing entry with updated content (new comments, state changes, etc.).

## Comment Ranking

Not all issue comments are equally useful. Context Teleport ranks comments by relevance and includes only the most informative ones in the synthesized knowledge entry.

Ranking criteria (in order of weight):

1. **Author association** -- OWNER > MEMBER > CONTRIBUTOR > COLLABORATOR > NONE
2. **Reactions** -- Comments with more reactions are ranked higher
3. **Code blocks** -- Comments containing code snippets are prioritized
4. **Position** -- Earlier comments that set context are weighted slightly higher

Comments that are skipped:

- Bot-authored comments (e.g., CI bots, stale bots)
- Very short comments (fewer than 20 characters)

A maximum of 10 top-ranked comments are included per issue by default.

## Decision Synthesis

The `--as-decisions` flag converts closed issues into structured decision records alongside the knowledge entry. This is useful for treating resolved issues as architectural decisions.

```bash
context-teleport import github --repo owner/repo --state closed --as-decisions
```

For each closed issue, this creates:

1. **A knowledge entry** (`github-issue-<slug>-<number>`) with the full synthesized discussion.
2. **A decision record** (ADR) with structured fields: title, context (from the issue body), decision text (from the resolution), and consequences (extracted from closing comments).

> **Note:** Decision synthesis works best with closed issues that have clear resolution comments. Open issues imported with `--as-decisions` produce only the knowledge entry.

## Full Command Reference

```
context-teleport import github [OPTIONS]

Options:
  -r, --repo TEXT        GitHub repository (owner/repo). Auto-detected if omitted.
  -i, --issue INTEGER    Import a single issue by number.
  -l, --labels TEXT      Comma-separated labels to filter by.
  -s, --state TEXT       Issue state: open, closed, all. [default: all]
  --since TEXT           Only issues created after this date (ISO format).
  -n, --limit INTEGER    Maximum number of issues to fetch. [default: 50]
  --as-decisions         Also create decision records for closed issues.
  --dry-run              Show what would be imported.
  --format TEXT          Output format: text or json.
```

## Example: Importing IHP-Open-PDK Issues as Decisions

This example imports closed bug reports from IHP-Open-PDK and records them as decisions.

```bash
# Initialize context store
cd /path/to/my-pdk-project
context-teleport init sg13g2-work

# Import closed issues labeled "bug" as both knowledge and decisions
context-teleport import github \
  --repo IHP-GmbH/IHP-Open-PDK \
  --state closed \
  --labels bug \
  --as-decisions \
  --limit 20

# Check what was imported
context-teleport knowledge list
# key                                          scope    updated
# github-issue-ihp-gmbh-ihp-open-pdk-835      public   2025-06-15
# github-issue-ihp-gmbh-ihp-open-pdk-812      public   2025-06-15
# ...

context-teleport decision list
# id    title                                  status     date
# 0001  Fix SG13G2 DRC rule for metal5 width   accepted   2025-06-15
# 0002  Update LVS netlist extraction flow      accepted   2025-06-15
# ...
```

Now any AI agent with MCP access can reference these resolved issues when working on the PDK. If the agent encounters a similar DRC rule violation, it can find the historical resolution in the knowledge store instead of rediscovering the fix from scratch.

## Combining with EDA Imports

GitHub issues and EDA artifact imports complement each other well. A typical workflow:

```bash
# Import design artifacts
context-teleport import eda config.json
context-teleport import eda results/signoff/inverter.drc

# Import relevant GitHub issues for context
context-teleport import github --repo IHP-GmbH/IHP-Open-PDK --labels drc --state closed --as-decisions

# The agent now has: design config + DRC results + historical DRC issue resolutions
```
