# Adding Adapters

How to implement a new adapter for an AI coding tool.

## Overview

An adapter bridges between Context Teleport's universal store and a tool-specific file layout. To add a new adapter, you implement the `AdapterProtocol` and register it in the adapter registry.

## Step 1: Implement the protocol

Create `src/ctx/adapters/newtool.py`:

```python
"""Adapter for NewTool."""

from __future__ import annotations

from pathlib import Path

from ctx.core.store import ContextStore


class NewToolAdapter:
    name = "newtool"

    def __init__(self, store: ContextStore, root: Path):
        self.store = store
        self.root = root

    def detect(self) -> bool:
        """Check if NewTool is available in this project."""
        # Look for tool-specific markers
        return (self.root / ".newtool").is_dir()

    def import_context(self, dry_run: bool = False) -> dict:
        """Import context from NewTool files into the store."""
        imported = []

        # Read tool-specific files
        config_file = self.root / ".newtool" / "context.md"
        if config_file.exists():
            content = config_file.read_text()
            if not dry_run:
                self.store.set_knowledge(
                    "newtool-context", content, author="import:newtool"
                )
            imported.append("newtool-context")

        # Import skills from tool's skill directory
        skills_dir = self.root / ".newtool" / "skills"
        if skills_dir.is_dir():
            for skill_dir in skills_dir.iterdir():
                skill_file = skill_dir / "SKILL.md"
                if skill_file.exists():
                    content = skill_file.read_text()
                    if not dry_run:
                        self.store.set_skill(
                            skill_dir.name, content, agent="import:newtool"
                        )
                    imported.append(f"skill:{skill_dir.name}")

        return {"imported": imported, "dry_run": dry_run}

    def export_context(self, dry_run: bool = False) -> dict:
        """Export store content to NewTool locations."""
        from ctx.core.scope import Scope

        exported = []
        knowledge = self.store.list_knowledge(scope=Scope.public)

        # Write to tool's expected location
        # Use managed sections if the file mixes user and managed content
        for entry in knowledge:
            if not dry_run:
                # Write to tool-specific format
                pass
            exported.append(entry.key)

        # Export skills
        skills = self.store.list_skills(scope=Scope.public)
        skills_dir = self.root / ".newtool" / "skills"
        for skill in skills:
            skill_dir = skills_dir / skill.name
            if not dry_run:
                skill_dir.mkdir(parents=True, exist_ok=True)
                (skill_dir / "SKILL.md").write_text(skill.content)
            exported.append(f"skill:{skill.name}")

        return {"exported": exported, "dry_run": dry_run}

    def mcp_config_path(self) -> Path | None:
        """Return the path to NewTool's MCP config file."""
        return self.root / ".newtool" / "mcp.json"

    def register_mcp(self, local: bool = False) -> dict:
        """Register context-teleport in NewTool's MCP config."""
        from ctx.adapters._mcp_reg import register_mcp_json

        config_path = self.mcp_config_path()
        return register_mcp_json(
            config_path=config_path,
            server_name="context-teleport",
            local=local,
            env={"MCP_CALLER": "mcp:newtool"},
        )

    def unregister_mcp(self) -> dict:
        """Remove context-teleport from NewTool's MCP config."""
        from ctx.adapters._mcp_reg import unregister_mcp_json

        config_path = self.mcp_config_path()
        return unregister_mcp_json(config_path, "context-teleport")
```

## Step 2: Register in the adapter registry

Edit `src/ctx/adapters/registry.py`:

```python
from ctx.adapters.newtool import NewToolAdapter

_ADAPTERS = {
    "claude-code": ClaudeCodeAdapter,
    "opencode": OpenCodeAdapter,
    "codex": CodexAdapter,
    "gemini": GeminiAdapter,
    "cursor": CursorAdapter,
    "newtool": NewToolAdapter,  # Add here
}
```

## Step 3: Write tests

Create `tests/adapters/test_newtool.py`:

```python
import pytest
from ctx.adapters.newtool import NewToolAdapter
from ctx.core.store import ContextStore


@pytest.fixture
def adapter(tmp_path):
    store = ContextStore(tmp_path)
    store.init(project_name="test")
    return NewToolAdapter(store, tmp_path)


def test_detect_no_markers(adapter):
    assert adapter.detect() is False


def test_detect_with_markers(adapter, tmp_path):
    (tmp_path / ".newtool").mkdir()
    assert adapter.detect() is True


def test_import_context(adapter, tmp_path):
    (tmp_path / ".newtool").mkdir()
    (tmp_path / ".newtool" / "context.md").write_text("Test content")
    result = adapter.import_context()
    assert "newtool-context" in result["imported"]


def test_export_skills(adapter, tmp_path):
    adapter.store.set_skill("test-skill", "---\nname: test-skill\n---\nContent")
    (tmp_path / ".newtool").mkdir()
    result = adapter.export_context()
    assert "skill:test-skill" in result["exported"]


def test_register_mcp(adapter, tmp_path):
    result = adapter.register_mcp()
    config = tmp_path / ".newtool" / "mcp.json"
    assert config.exists()
```

## Shared modules

Use the existing shared modules when possible:

- **`_mcp_reg.py`**: For JSON-based MCP config registration. Handles read/update/write of `mcpServers` config.
- **`_agents_md.py`**: For tools that use `AGENTS.md` with managed sections (delimited by `ctx:start`/`ctx:end` markers).

## Checklist

- [ ] Implement all 6 `AdapterProtocol` methods
- [ ] `detect()` checks for tool-specific markers (directories, config files)
- [ ] `import_context()` reads tool files, writes to store with `author="import:newtool"`
- [ ] `export_context()` writes only public-scope entries
- [ ] `register_mcp()` sets `MCP_CALLER` env var for agent attribution
- [ ] Skills import/export uses `SKILL.md` format in `<tool-dir>/skills/*/SKILL.md`
- [ ] `--dry-run` support on import and export
- [ ] Tests cover detect, import, export, register, and unregister
- [ ] Adapter registered in `registry.py`
- [ ] README adapter table updated
