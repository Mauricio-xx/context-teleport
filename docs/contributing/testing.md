# Testing

Context Teleport has 701 tests covering all components. This guide explains the test architecture, how to run specific subsets, and patterns used in the test suite.

## Running tests

```bash
# Full suite
pytest tests/ -v

# Specific module
pytest tests/core/ -v
pytest tests/mcp/ -v
pytest tests/adapters/ -v
pytest tests/eda/ -v
pytest tests/sources/ -v
pytest tests/cli/ -v

# Single file
pytest tests/adapters/test_gemini.py -v

# Pattern matching
pytest tests/ -v -k "test_skill"
```

## Test structure

```
tests/
  core/              # Schema, store, search, scope, merge, migrations, frontmatter
  mcp/
    test_unit.py     # MCP tool/resource unit tests (mock store)
    test_e2e.py      # End-to-end tests (real subprocess)
  adapters/          # Per-adapter tests + registration E2E
  sync/              # Git sync, push/pull, conflict resolution
  cli/               # CLI command tests
  eda/
    parsers/         # Per-parser tests
    test_detect.py   # Project detection tests
    test_cli.py      # EDA CLI integration
  sources/
    test_github.py   # GitHub source unit tests (mocked subprocess)
    test_github_cli.py # CLI integration tests
```

## Test breakdown

| Module | Tests | Notes |
|--------|-------|-------|
| Core (store, schema, search, etc.) | ~160 | Pydantic models, store CRUD, search ranking |
| MCP unit | ~95 | Tools and resources via `set_store()` injection |
| MCP E2E | 28 | Real subprocess via `mcp.client.stdio.stdio_client` |
| Registration E2E | 6 | Full adapter MCP registration cycle |
| Adapters | ~66 | Per-adapter import/export, shared modules |
| Sync | 23 | Two-repo fixture, section merge, conflicts |
| CLI | ~54 | Typer test runner for all subcommands |
| Migrations | ~10 | Schema version upgrades |
| Frontmatter | 13 | YAML frontmatter parsing/building |
| EDA parsers | ~83 | Per-parser file handling |
| EDA detect | 13 | Project type detection |
| EDA CLI | 11 | Import command integration |
| Sources (GitHub) | 42 | Mocked `gh` CLI subprocess calls |
| Sources CLI | 12 | GitHub import command integration |

## Key patterns

### Store injection for MCP unit tests

MCP unit tests use `set_store()` to inject a mock store, avoiding filesystem setup:

```python
from ctx.mcp.server import set_store

def test_add_knowledge(tmp_path):
    store = ContextStore(tmp_path)
    store.init(project_name="test")
    set_store(store)

    result = context_add_knowledge("arch", "content")
    assert "ok" in result
```

### E2E tests with real subprocess

E2E tests spawn the actual MCP server as a subprocess and communicate via stdio:

```python
from mcp.client.stdio import stdio_client

async def test_e2e_search():
    async with stdio_client(["python", "-m", "ctx.mcp.server"]) as client:
        result = await client.call_tool("context_search", {"query": "test"})
        ...
```

### Two-repo sync fixture

Sync tests use a fixture that creates:

1. A **seed** repository with initial content
2. A **bare upstream** (clone of seed)
3. **Two clones** of the upstream (simulating two developers)

This enables testing push/pull/conflict scenarios with real git operations.

### Async test support

Tests use `anyio_mode = "auto"` (configured in `pyproject.toml`) for async test support. Async tests are decorated with `@pytest.mark.anyio`.

### Mocked subprocess for GitHub tests

GitHub source tests mock `subprocess.run` to simulate `gh` CLI output without requiring GitHub authentication:

```python
def test_fetch_issues(monkeypatch):
    monkeypatch.setattr("subprocess.run", mock_gh_response)
    source = GitHubSource()
    items = source.fetch_issues(config)
    ...
```

## Known issues

- `test_generate_instructions_fallback` has a pre-existing failure due to instruction text drift. Not a real bug -- the test expectation needs updating.
- Some older files have pre-existing ruff warnings. New code should be clean.

## Writing new tests

1. Place tests in the appropriate module directory
2. Use `tmp_path` fixture for filesystem tests
3. Use `set_store()` for MCP tool tests
4. Mock external dependencies (subprocess, network)
5. Name test files `test_<module>.py` and test functions `test_<behavior>`
