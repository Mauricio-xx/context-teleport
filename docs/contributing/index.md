# Contributing

Thanks for considering contributing to Context Teleport. This section covers everything you need to get started.

## Development setup

```bash
git clone https://github.com/Mauricio-xx/context-teleport.git
cd context-teleport
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Optional: watchdog support for context-teleport watch
pip install -e ".[watch]"
```

## Running tests

```bash
# Full suite (701 tests)
pytest tests/ -v

# Specific modules
pytest tests/adapters/ -v
pytest tests/mcp/ -v
pytest tests/eda/ -v
pytest tests/sources/ -v
```

See **[Testing](testing.md)** for the full test architecture guide.

## Linting

```bash
ruff check src/ tests/
```

Code should pass `ruff check` with no new warnings. Existing files may have pre-existing warnings -- do not fix unrelated lint in your PR.

## Code style

- Python 3.11+ features are fine (`|` union types, `match` statements, etc.)
- Type hints on public functions
- Docstrings on modules, classes, and public methods
- Line length: 100 characters (configured in `pyproject.toml`)

## Pull request process

1. Fork and create a feature branch from `main`
2. Write tests for new functionality
3. Ensure `pytest tests/ -v` passes and `ruff check src/ tests/` is clean
4. Open a PR against `main` with a clear description
5. Your first PR constitutes agreement to the [CLA](https://github.com/Mauricio-xx/context-teleport/blob/main/CLA.md)

## Extending Context Teleport

- **[Adding Adapters](adding-adapters.md)** -- How to implement support for a new agent tool
- **[Adding EDA Parsers](adding-eda-parsers.md)** -- How to implement a new EDA artifact parser
