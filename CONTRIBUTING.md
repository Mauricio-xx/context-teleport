# Contributing to Context Teleport

Thanks for considering contributing. Here is what you need to know.

## Development setup

```bash
git clone https://github.com/Mauricio-xx/context-teleport.git
cd context-teleport
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Running tests

```bash
# Full suite
pytest tests/ -v

# Specific module
pytest tests/adapters/test_gemini.py -v

# MCP E2E tests
pytest tests/mcp/test_e2e.py -v
```

## Linting

```bash
ruff check src/ tests/
```

Code should pass `ruff check` with no new warnings. Existing files may have pre-existing warnings -- don't fix unrelated lint in your PR.

## Code style

- Python 3.11+ features are fine (union types with `|`, `match` statements, etc.)
- Type hints on public functions
- Docstrings on modules, classes, and public methods
- Line length: 100 characters (configured in `pyproject.toml`)

## Pull request process

1. Fork and create a feature branch from `main`
2. Write tests for new functionality
3. Ensure `pytest tests/ -v` passes and `ruff check src/ tests/` is clean
4. Open a PR against `main` with a clear description of the change
5. Your first PR constitutes agreement to the [CLA](CLA.md)

## Contributor License Agreement

All contributions require signing the project CLA. By submitting your first pull request, you agree to the terms in [CLA.md](CLA.md). This enables dual-licensing (AGPL-3.0 open source + commercial).

## What to work on

Check [Issues](https://github.com/Mauricio-xx/context-teleport/issues) for open items. Good first issues are labeled accordingly.
