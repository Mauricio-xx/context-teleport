# Installation

Context Teleport runs on Python 3.11+ and requires Git. There are three ways to install it, depending on your workflow.

## Prerequisites

Before installing, make sure you have:

- **Python 3.11 or newer** -- check with `python3 --version`
- **Git** -- check with `git --version`
- An MCP-compatible agent tool: Claude Code, OpenCode, Cursor, Gemini, or Codex

## Method 1: uvx (recommended)

[uvx](https://docs.astral.sh/uv/) runs Python tools on demand without installing them permanently. This is the recommended approach because it keeps your environment clean and always uses the latest version.

```bash
uvx context-teleport --help
```

That is it. No `pip install`, no virtual environment to manage. The `uvx` resolver downloads and caches the package automatically.

When you register with an agent tool, the MCP configuration uses `uvx` as the command, so the agent spawns Context Teleport the same way:

```bash
uvx context-teleport init --name my-project
uvx context-teleport register claude-code
```

!!! tip "How uvx registration works"
    After `register`, the MCP config file (e.g. `.claude/mcp.json`) contains an entry that runs `uvx context-teleport` as the server command. You do not need to activate anything -- the agent tool handles startup automatically.

!!! info "Installing uv"
    If you do not have `uv` installed yet:

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

    See the [uv documentation](https://docs.astral.sh/uv/getting-started/installation/) for other methods.


## Method 2: pip install

Install from PyPI into a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install context-teleport
```

Verify the installation:

```bash
context-teleport --help
```

You should see the full CLI help with subcommands for `init`, `register`, `status`, `knowledge`, `decision`, `skill`, `sync`, and more.

### Optional extras

Context Teleport ships with optional dependency groups for specific features:

=== "File watching"

    Enables filesystem monitoring with `watchdog` for the `context-teleport watch` command. Without this, watch mode falls back to polling.

    ```bash
    pip install context-teleport[watch]
    ```

=== "Documentation"

    Installs `mkdocs-material` and plugins for building the documentation site locally.

    ```bash
    pip install context-teleport[docs]
    ```

=== "Development"

    Includes `pytest`, `ruff`, and `anyio` for running the test suite and linting.

    ```bash
    pip install context-teleport[dev]
    ```

## Method 3: From source

Clone the repository and install in editable mode. This is useful for contributing or running the latest unreleased code.

```bash
git clone https://github.com/Mauricio-xx/context-teleport.git
cd context-teleport
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Verify with:

```bash
context-teleport --help
```

!!! warning "Use `--local` when registering from source"
    When running from a source checkout, pass `--local` to the register command so the MCP config points to your local `context-teleport` binary instead of `uvx`:

    ```bash
    context-teleport register claude-code --local
    ```

    Without `--local`, the config will try to use `uvx`, which would pull the PyPI version instead of your local edits.

### Running tests

```bash
pytest tests/ -v
```

The full suite has 930+ tests covering core logic, MCP tools, CLI, adapters, sync, EDA parsers, and source importers.


## Verifying the installation

Regardless of install method, confirm everything works:

```bash
# Show version and available commands
context-teleport --help

# Initialize a test store
context-teleport init --name test-project

# Check store status
context-teleport status
```

You should see output confirming the store was initialized with a `.context-teleport/` directory in your project root.


## How the entry point works

Context Teleport uses a single binary (`context-teleport`) with smart dispatch:

- **Interactive terminal + arguments** -- runs the CLI (Typer app)
- **Non-interactive stdin + no arguments** -- runs the MCP server (FastMCP over stdio)

This means agent tools can spawn it as an MCP server by piping stdin, while you use the exact same command for CLI operations in your terminal. You never need to think about this -- `register` sets up the MCP config correctly, and you use the CLI directly.


## Next steps

With Context Teleport installed, head to the [Quickstart](quickstart.md) to initialize your first store and register it with your agent tool.
