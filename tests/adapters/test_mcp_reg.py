"""Tests for shared MCP registration helpers."""

import json

from ctx.adapters._mcp_reg import (
    register_mcp_json,
    register_mcp_opencode,
    unregister_mcp_json,
    unregister_mcp_opencode,
    SERVER_NAME,
)


class TestRegisterMcpJson:
    def test_creates_new_file(self, tmp_path):
        config_path = tmp_path / ".claude" / "mcp.json"
        result = register_mcp_json(config_path)
        assert result["status"] == "registered"
        assert config_path.is_file()
        config = json.loads(config_path.read_text())
        assert SERVER_NAME in config["mcpServers"]

    def test_idempotent(self, tmp_path):
        config_path = tmp_path / "mcp.json"
        register_mcp_json(config_path)
        register_mcp_json(config_path)
        config = json.loads(config_path.read_text())
        assert len(config["mcpServers"]) == 1

    def test_merges_with_existing(self, tmp_path):
        config_path = tmp_path / "mcp.json"
        config_path.write_text(json.dumps({
            "mcpServers": {"other-server": {"command": "other"}}
        }))
        register_mcp_json(config_path)
        config = json.loads(config_path.read_text())
        assert "other-server" in config["mcpServers"]
        assert SERVER_NAME in config["mcpServers"]

    def test_custom_server_name(self, tmp_path):
        config_path = tmp_path / "mcp.json"
        result = register_mcp_json(config_path, server_name="custom")
        assert result["server"] == "custom"
        config = json.loads(config_path.read_text())
        assert "custom" in config["mcpServers"]


class TestUnregisterMcpJson:
    def test_removes_entry(self, tmp_path):
        config_path = tmp_path / "mcp.json"
        register_mcp_json(config_path)
        result = unregister_mcp_json(config_path)
        assert result["status"] == "unregistered"
        config = json.loads(config_path.read_text())
        assert SERVER_NAME not in config["mcpServers"]

    def test_handles_missing_file(self, tmp_path):
        config_path = tmp_path / "mcp.json"
        result = unregister_mcp_json(config_path)
        assert result["status"] == "not_registered"

    def test_handles_not_registered(self, tmp_path):
        config_path = tmp_path / "mcp.json"
        config_path.write_text(json.dumps({"mcpServers": {}}))
        result = unregister_mcp_json(config_path)
        assert result["status"] == "not_registered"

    def test_preserves_other_servers(self, tmp_path):
        config_path = tmp_path / "mcp.json"
        config_path.write_text(json.dumps({
            "mcpServers": {
                SERVER_NAME: {"command": "ctx-mcp"},
                "other": {"command": "other-cmd"},
            }
        }))
        unregister_mcp_json(config_path)
        config = json.loads(config_path.read_text())
        assert "other" in config["mcpServers"]
        assert SERVER_NAME not in config["mcpServers"]


class TestRegisterMcpOpencode:
    """Tests for OpenCode-specific registration (different JSON schema)."""

    def test_creates_new_file(self, tmp_path):
        config_path = tmp_path / "opencode.json"
        result = register_mcp_opencode(config_path, caller_name="mcp:opencode")
        assert result["status"] == "registered"
        config = json.loads(config_path.read_text())
        assert "mcp" in config
        assert SERVER_NAME in config["mcp"]

    def test_entry_uses_local_type(self, tmp_path):
        config_path = tmp_path / "opencode.json"
        register_mcp_opencode(config_path, caller_name="mcp:opencode")
        config = json.loads(config_path.read_text())
        entry = config["mcp"][SERVER_NAME]
        assert entry["type"] == "local"

    def test_command_is_array(self, tmp_path):
        config_path = tmp_path / "opencode.json"
        register_mcp_opencode(config_path)
        config = json.loads(config_path.read_text())
        entry = config["mcp"][SERVER_NAME]
        assert isinstance(entry["command"], list)
        assert entry["command"] == [
            "uvx", "--from", "context-teleport", "python", "-m", "ctx.mcp.server",
        ]

    def test_local_mode(self, tmp_path):
        config_path = tmp_path / "opencode.json"
        register_mcp_opencode(config_path, local=True)
        config = json.loads(config_path.read_text())
        entry = config["mcp"][SERVER_NAME]
        assert entry["command"] == ["python", "-m", "ctx.mcp.server"]

    def test_uses_environment_key(self, tmp_path):
        """OpenCode uses 'environment' not 'env'."""
        config_path = tmp_path / "opencode.json"
        register_mcp_opencode(config_path, caller_name="mcp:opencode")
        config = json.loads(config_path.read_text())
        entry = config["mcp"][SERVER_NAME]
        assert "env" not in entry
        assert entry["environment"] == {"MCP_CALLER": "mcp:opencode"}

    def test_no_extra_fields(self, tmp_path):
        """OpenCode schema is strict -- only known fields allowed."""
        config_path = tmp_path / "opencode.json"
        register_mcp_opencode(config_path, caller_name="mcp:opencode")
        config = json.loads(config_path.read_text())
        entry = config["mcp"][SERVER_NAME]
        allowed = {"type", "command", "environment"}
        assert set(entry.keys()) <= allowed

    def test_idempotent(self, tmp_path):
        config_path = tmp_path / "opencode.json"
        register_mcp_opencode(config_path)
        register_mcp_opencode(config_path)
        config = json.loads(config_path.read_text())
        assert len(config["mcp"]) == 1

    def test_preserves_existing_config(self, tmp_path):
        config_path = tmp_path / "opencode.json"
        config_path.write_text(json.dumps({
            "$schema": "https://opencode.ai/config.json",
            "mcp": {"other-server": {"type": "local", "command": ["other"]}},
        }))
        register_mcp_opencode(config_path)
        config = json.loads(config_path.read_text())
        assert "$schema" in config
        assert "other-server" in config["mcp"]
        assert SERVER_NAME in config["mcp"]


class TestUnregisterMcpOpencode:
    def test_removes_entry(self, tmp_path):
        config_path = tmp_path / "opencode.json"
        register_mcp_opencode(config_path)
        result = unregister_mcp_opencode(config_path)
        assert result["status"] == "unregistered"
        config = json.loads(config_path.read_text())
        assert SERVER_NAME not in config["mcp"]

    def test_handles_missing_file(self, tmp_path):
        config_path = tmp_path / "opencode.json"
        result = unregister_mcp_opencode(config_path)
        assert result["status"] == "not_registered"

    def test_preserves_other_servers(self, tmp_path):
        config_path = tmp_path / "opencode.json"
        config_path.write_text(json.dumps({
            "mcp": {
                SERVER_NAME: {"type": "local", "command": ["ctx"]},
                "other": {"type": "local", "command": ["other"]},
            }
        }))
        unregister_mcp_opencode(config_path)
        config = json.loads(config_path.read_text())
        assert "other" in config["mcp"]
        assert SERVER_NAME not in config["mcp"]
