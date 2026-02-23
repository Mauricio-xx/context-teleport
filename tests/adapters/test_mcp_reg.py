"""Tests for shared MCP registration helpers."""

import json

from ctx.adapters._mcp_reg import register_mcp_json, unregister_mcp_json, SERVER_NAME


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
