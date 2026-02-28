"""Tests for Claude Code lifecycle hooks generation."""

import json

from ctx.adapters.claude_code import ClaudeCodeAdapter


class TestBuildHooksConfig:
    def test_returns_expected_events(self, store):
        adapter = ClaudeCodeAdapter(store)
        config = adapter._build_hooks_config()
        assert "PreCompact" in config
        assert "SessionStart" in config
        assert "SubagentStart" in config

    def test_pre_compact_has_matcher(self, store):
        adapter = ClaudeCodeAdapter(store)
        config = adapter._build_hooks_config()
        entry = config["PreCompact"][0]
        assert entry["matcher"] == "manual|auto"
        assert len(entry["hooks"]) == 1
        assert entry["hooks"][0]["type"] == "command"

    def test_session_start_targets_compact(self, store):
        adapter = ClaudeCodeAdapter(store)
        config = adapter._build_hooks_config()
        entry = config["SessionStart"][0]
        assert entry["matcher"] == "compact"
        assert "context_onboarding" in entry["hooks"][0]["command"]

    def test_subagent_start_has_empty_matcher(self, store):
        adapter = ClaudeCodeAdapter(store)
        config = adapter._build_hooks_config()
        entry = config["SubagentStart"][0]
        assert entry["matcher"] == ""
        assert "context-teleport" in entry["hooks"][0]["command"]


class TestInstallHooks:
    def test_install_creates_settings_file(self, store):
        adapter = ClaudeCodeAdapter(store)
        result = adapter.install_hooks()
        assert result["status"] == "installed"
        settings_path = store.root / ".claude" / "settings.json"
        assert settings_path.is_file()

        settings = json.loads(settings_path.read_text())
        assert "hooks" in settings
        assert "PreCompact" in settings["hooks"]
        assert "SessionStart" in settings["hooks"]
        assert "SubagentStart" in settings["hooks"]

    def test_install_dry_run(self, store):
        adapter = ClaudeCodeAdapter(store)
        result = adapter.install_hooks(dry_run=True)
        assert result["status"] == "dry_run"
        assert "PreCompact" in result["hooks"]
        # File should NOT be created
        settings_path = store.root / ".claude" / "settings.json"
        assert not settings_path.is_file()

    def test_install_preserves_existing_settings(self, store):
        settings_path = store.root / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps({
            "permissions": {"allow": ["Read"]},
            "hooks": {
                "PostToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "echo ok"}]}],
            },
        }))

        adapter = ClaudeCodeAdapter(store)
        adapter.install_hooks()

        settings = json.loads(settings_path.read_text())
        # Existing non-hook settings preserved
        assert settings["permissions"]["allow"] == ["Read"]
        # Existing non-ctx hooks preserved
        assert "PostToolUse" in settings["hooks"]
        # Ctx hooks added
        assert "PreCompact" in settings["hooks"]

    def test_install_is_idempotent(self, store):
        adapter = ClaudeCodeAdapter(store)
        adapter.install_hooks()
        result = adapter.install_hooks()
        assert result["status"] == "installed"

        settings = json.loads((store.root / ".claude" / "settings.json").read_text())
        # Only one PreCompact entry (not duplicated)
        assert len(settings["hooks"]["PreCompact"]) == 1

    def test_install_handles_corrupted_settings(self, store):
        settings_path = store.root / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text("not valid json")

        adapter = ClaudeCodeAdapter(store)
        result = adapter.install_hooks()
        assert result["status"] == "installed"
        # Should create valid settings
        settings = json.loads(settings_path.read_text())
        assert "hooks" in settings


class TestUninstallHooks:
    def test_uninstall_removes_ctx_hooks(self, store):
        adapter = ClaudeCodeAdapter(store)
        adapter.install_hooks()
        result = adapter.uninstall_hooks()
        assert result["status"] == "uninstalled"
        assert "PreCompact" in result["removed"]

        settings = json.loads((store.root / ".claude" / "settings.json").read_text())
        assert "PreCompact" not in settings["hooks"]
        assert "SessionStart" not in settings["hooks"]
        assert "SubagentStart" not in settings["hooks"]

    def test_uninstall_preserves_other_hooks(self, store):
        settings_path = store.root / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps({
            "hooks": {
                "PostToolUse": [{"matcher": "Edit", "hooks": [{"type": "command", "command": "echo ok"}]}],
            },
        }))

        adapter = ClaudeCodeAdapter(store)
        adapter.install_hooks()
        adapter.uninstall_hooks()

        settings = json.loads(settings_path.read_text())
        assert "PostToolUse" in settings["hooks"]

    def test_uninstall_no_settings_file(self, store):
        adapter = ClaudeCodeAdapter(store)
        result = adapter.uninstall_hooks()
        assert result["status"] == "no_settings"

    def test_uninstall_no_hooks(self, store):
        settings_path = store.root / ".claude" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text(json.dumps({"permissions": {}}))

        adapter = ClaudeCodeAdapter(store)
        result = adapter.uninstall_hooks()
        assert result["status"] == "no_hooks"


class TestRegisterIncludesHooks:
    def test_register_mcp_installs_hooks(self, store):
        adapter = ClaudeCodeAdapter(store)
        result = adapter.register_mcp(local=True)
        assert result["status"] == "registered"
        assert "hooks" in result
        assert result["hooks"]["status"] == "installed"

        # MCP config created
        assert (store.root / ".claude" / "mcp.json").is_file()
        # Hooks settings created
        assert (store.root / ".claude" / "settings.json").is_file()

    def test_unregister_mcp_uninstalls_hooks(self, store):
        adapter = ClaudeCodeAdapter(store)
        adapter.register_mcp(local=True)
        result = adapter.unregister_mcp()
        assert "hooks" in result
