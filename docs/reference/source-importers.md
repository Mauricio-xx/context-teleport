# Source Importers

Source importers fetch context from external services and synthesize it into knowledge entries and decisions. Unlike adapters (bidirectional, model AI tools) and EDA parsers (local files), source importers connect to remote APIs.

## Architecture

The `src/ctx/sources/` package is separate from adapters and EDA parsers:

- **Adapters** (`src/ctx/adapters/`): bidirectional import/export for AI tools
- **EDA parsers** (`src/ctx/eda/parsers/`): import-only, local files
- **Sources** (`src/ctx/sources/`): import-only, remote services

## Data models

### SourceConfig

Configuration for a source import operation:

```python
@dataclass
class SourceConfig:
    repo: str                         # "owner/repo" (required)
    labels: list[str] = []            # Filter by labels
    state: str = "all"                # "open", "closed", "all"
    since: str = ""                   # ISO date filter
    issue_number: int | None = None   # Single issue import
    limit: int = 50                   # Max issues to fetch
    as_decisions: bool = False        # Import closed issues as decisions
```

### SourceItem

A single item produced by a source importer:

```python
@dataclass
class SourceItem:
    type: str           # "knowledge" or "decision"
    key: str            # e.g. "github-issue-ihp-open-pdk-835"
    content: str        # Synthesized markdown
    source: str         # Origin URL or reference

    # Decision-specific fields (populated when type == "decision")
    title: str = ""
    context: str = ""
    decision_text: str = ""
    consequences: str = ""
```

## GitHub Source

The `GitHubSource` class (`src/ctx/sources/github.py`) imports GitHub issues as knowledge entries or decisions.

### Why `gh` CLI

The implementation uses the `gh` CLI instead of PyGithub or the REST API directly:

- Zero additional dependencies
- Authentication handled by `gh auth`
- JSON output via `--json` flag
- Consistent with the project's subprocess patterns

!!! warning "Prerequisite"
    The `gh` CLI must be installed and authenticated (`gh auth login`) before using the GitHub source importer.

### Key pattern

Issues are stored with the key pattern: `github-issue-<repo-slug>-<number>`

Example: `github-issue-ihp-open-pdk-835`

### Repo auto-detection

When `--repo` is not specified, `GitHubSource` parses `git remote -v` output to detect the GitHub repository from SSH or HTTPS patterns.

### Comment ranking

When synthesizing issue content, comments are ranked by quality:

1. **Author association**: OWNER > MEMBER > CONTRIBUTOR > others
2. **Reactions**: Higher reaction count ranks higher
3. **Code blocks**: Comments with code are preferred
4. **Position**: Later comments break ties

Bot comments and very short comments (under 20 characters) are filtered out.

### Decision synthesis

When `--as-decisions` is used with closed issues:

- A **knowledge entry** is created with the full synthesized issue content
- A **decision record** (ADR) is also created with:
    - `title`: Issue title
    - `context`: Issue body (truncated)
    - `decision_text`: Resolution from closing comment or top-ranked comment
    - `consequences`: Extracted from issue labels and milestone

### Methods

| Method | Description |
|--------|-------------|
| `fetch_issues(config)` | Fetch issues from GitHub via `gh` CLI |
| `fetch_single_issue(config)` | Fetch a single issue by number |
| `synthesize_issue(issue_data)` | Convert raw issue JSON to markdown |
| `import_issues(config, store)` | Full pipeline: fetch, synthesize, write to store |
| `detect_repo()` | Auto-detect repo from git remote |

## CLI usage

### Import all open issues

```bash
context-teleport import github --repo owner/repo
```

### Import a single issue

```bash
context-teleport import github --issue 835
```

### Filter by labels

```bash
context-teleport import github --repo owner/repo --labels bug,critical
```

### Import closed issues as decisions

```bash
context-teleport import github --repo owner/repo --state closed --as-decisions
```

### Filter by date

```bash
context-teleport import github --since 2025-01-01
```

### Preview without writing

```bash
context-teleport import github --repo owner/repo --dry-run
```

### All options

| Option | Default | Description |
|--------|---------|-------------|
| `--repo` | Auto-detected | Repository in `owner/repo` format |
| `--issue` | -- | Single issue number to import |
| `--labels` | -- | Comma-separated label filter |
| `--state` | `all` | Issue state: `open`, `closed`, `all` |
| `--since` | -- | ISO date filter (e.g. `2025-01-01`) |
| `--limit` | 50 | Maximum number of issues to fetch |
| `--as-decisions` | `False` | Also create decision records for closed issues |
| `--dry-run` | `False` | Preview without writing |
| `--format` | `text` | Output format: `text` or `json` |
