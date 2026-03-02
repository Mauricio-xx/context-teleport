"""Schema contract tests: validate generated MCP configs against each tool's real JSON schema.

These tests exist because two critical bugs shipped undetected -- Claude Code wrote
to the wrong path and OpenCode used the wrong JSON schema. The root cause was that
tests validated internal consistency without checking against what the target tools
actually expect. These contract tests maintain the real schemas and validate against
them, catching format regressions immediately.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from ctx.adapters.claude_code import ClaudeCodeAdapter
from ctx.adapters.cursor import CursorAdapter
from ctx.adapters.gemini import GeminiAdapter
from ctx.adapters.opencode import OpenCodeAdapter
from ctx.core.store import ContextStore

SCHEMA_DIR = Path(__file__).parent / "schemas"

ADAPTERS = {
    "claude_code": ClaudeCodeAdapter,
    "cursor": CursorAdapter,
    "gemini": GeminiAdapter,
    "opencode": OpenCodeAdapter,
}


@pytest.fixture
def store(tmp_path):
    s = ContextStore(tmp_path)
    s.init(project_name="test-schema-contracts")
    return s


@pytest.fixture
def schemas():
    """Load all schema files from the schemas directory."""
    result = {}
    for name in ["claude_code", "cursor", "gemini", "opencode"]:
        schema_path = SCHEMA_DIR / f"{name}.schema.json"
        result[name] = json.loads(schema_path.read_text())
    return result


def _read_config(path: Path) -> dict:
    """Read and parse a JSON config file."""
    assert path.is_file(), f"Config file not created: {path}"
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Schema validation: uvx mode (default)
# ---------------------------------------------------------------------------


class TestSchemaValidationUvx:
    """Validate generated MCP configs in uvx mode against each tool's schema."""

    def test_claude_code(self, store, schemas):
        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp(local=False)
        config = _read_config(adapter.mcp_config_path())
        jsonschema.validate(config, schemas["claude_code"])

    def test_cursor(self, store, schemas):
        adapter = CursorAdapter(store)
        adapter.register_mcp(local=False)
        config = _read_config(adapter.mcp_config_path())
        jsonschema.validate(config, schemas["cursor"])

    def test_gemini(self, store, schemas):
        adapter = GeminiAdapter(store)
        adapter.register_mcp(local=False)
        config = _read_config(adapter.mcp_config_path())
        jsonschema.validate(config, schemas["gemini"])

    def test_opencode(self, store, schemas):
        adapter = OpenCodeAdapter(store)
        adapter.register_mcp(local=False)
        config = _read_config(adapter.mcp_config_path())
        jsonschema.validate(config, schemas["opencode"])


# ---------------------------------------------------------------------------
# Schema validation: local mode
# ---------------------------------------------------------------------------


class TestSchemaValidationLocal:
    """Validate generated MCP configs in local mode against each tool's schema."""

    def test_claude_code(self, store, schemas):
        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp(local=True)
        config = _read_config(adapter.mcp_config_path())
        jsonschema.validate(config, schemas["claude_code"])

    def test_cursor(self, store, schemas):
        adapter = CursorAdapter(store)
        adapter.register_mcp(local=True)
        config = _read_config(adapter.mcp_config_path())
        jsonschema.validate(config, schemas["cursor"])

    def test_gemini(self, store, schemas):
        adapter = GeminiAdapter(store)
        adapter.register_mcp(local=True)
        config = _read_config(adapter.mcp_config_path())
        jsonschema.validate(config, schemas["gemini"])

    def test_opencode(self, store, schemas):
        adapter = OpenCodeAdapter(store)
        adapter.register_mcp(local=True)
        config = _read_config(adapter.mcp_config_path())
        jsonschema.validate(config, schemas["opencode"])


# ---------------------------------------------------------------------------
# Config path validation
# ---------------------------------------------------------------------------


class TestConfigPaths:
    """Verify each adapter writes to the correct config file path."""

    def test_claude_code_writes_to_mcp_json(self, store):
        """Claude Code must write to .mcp.json at project root (not .claude/mcp.json)."""
        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp()
        expected = store.root / ".mcp.json"
        assert expected.is_file(), f"Expected {expected}, got {adapter.mcp_config_path()}"
        assert adapter.mcp_config_path() == expected

    def test_cursor_writes_to_cursor_mcp_json(self, store):
        """Cursor must write to .cursor/mcp.json."""
        adapter = CursorAdapter(store)
        adapter.register_mcp()
        expected = store.root / ".cursor" / "mcp.json"
        assert expected.is_file()
        assert adapter.mcp_config_path() == expected

    def test_gemini_writes_to_gemini_settings(self, store):
        """Gemini must write to .gemini/settings.json."""
        adapter = GeminiAdapter(store)
        adapter.register_mcp()
        expected = store.root / ".gemini" / "settings.json"
        assert expected.is_file()
        assert adapter.mcp_config_path() == expected

    def test_opencode_writes_to_opencode_json(self, store):
        """OpenCode must write to opencode.json at project root."""
        adapter = OpenCodeAdapter(store)
        adapter.register_mcp()
        expected = store.root / "opencode.json"
        assert expected.is_file()
        assert adapter.mcp_config_path() == expected


# ---------------------------------------------------------------------------
# Semantic validation (beyond JSON Schema)
# ---------------------------------------------------------------------------


class TestSemanticContracts:
    """Validate semantic properties that JSON Schema alone cannot enforce."""

    def test_all_adapters_set_mcp_caller(self, store):
        """Every adapter must set MCP_CALLER in the environment for agent attribution."""
        expected_callers = {
            "claude_code": "mcp:claude-code",
            "cursor": "mcp:cursor",
            "gemini": "mcp:gemini",
            "opencode": "mcp:opencode",
        }
        for name, cls in ADAPTERS.items():
            adapter = cls(store)
            adapter.register_mcp()
            config = _read_config(adapter.mcp_config_path())

            if name == "opencode":
                entry = config["mcp"]["context-teleport"]
                env = entry.get("environment", {})
            else:
                entry = config["mcpServers"]["context-teleport"]
                env = entry.get("env", {})

            assert "MCP_CALLER" in env, f"{name}: MCP_CALLER not set"
            assert env["MCP_CALLER"] == expected_callers[name], (
                f"{name}: MCP_CALLER={env['MCP_CALLER']!r}, expected {expected_callers[name]!r}"
            )

    def test_all_adapters_invoke_python_m_server(self, store):
        """Every adapter command must invoke 'python -m ctx.mcp.server'."""
        for name, cls in ADAPTERS.items():
            adapter = cls(store)
            adapter.register_mcp()
            config = _read_config(adapter.mcp_config_path())

            if name == "opencode":
                entry = config["mcp"]["context-teleport"]
                cmd_parts = entry["command"]
            else:
                entry = config["mcpServers"]["context-teleport"]
                cmd_parts = [entry["command"]] + entry.get("args", [])

            assert "python" in cmd_parts, f"{name}: 'python' not in command"
            assert "-m" in cmd_parts, f"{name}: '-m' not in command"
            assert "ctx.mcp.server" in cmd_parts, f"{name}: 'ctx.mcp.server' not in command"

            # Verify python -m ctx.mcp.server appears as consecutive args
            for i, part in enumerate(cmd_parts):
                if part == "python" and i + 2 < len(cmd_parts):
                    if cmd_parts[i + 1] == "-m" and cmd_parts[i + 2] == "ctx.mcp.server":
                        break
            else:
                pytest.fail(f"{name}: 'python -m ctx.mcp.server' not found as consecutive args")
