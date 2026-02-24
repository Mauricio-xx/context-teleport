"""Tests for ctx config subcommands."""

import json
import os

import git
import pytest
from typer.testing import CliRunner

from ctx.cli.main import app

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path):
    """Create a git repo and chdir into it."""
    repo = git.Repo.init(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    original = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original)


@pytest.fixture
def initialized_project(project_dir):
    """Project with ctx init already run."""
    result = runner.invoke(app, ["init", "--name", "test-project"])
    assert result.exit_code == 0
    return project_dir


@pytest.fixture
def clean_config(monkeypatch, tmp_path):
    """Redirect global config dir to a temp directory."""
    config_dir = tmp_path / "config"
    monkeypatch.setattr("ctx.utils.config.global_config_dir", lambda: config_dir)
    monkeypatch.setattr("ctx.cli.config_cmd.load_global_config", lambda: _load(config_dir))
    monkeypatch.setattr("ctx.cli.config_cmd.save_global_config", lambda c: _save(config_dir, c))
    return config_dir


def _load(config_dir):
    path = config_dir / "config.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save(config_dir, config):
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "config.json"
    path.write_text(json.dumps(config, indent=2))


class TestConfigSetGet:
    def test_set_and_get(self, initialized_project, clean_config):
        result = runner.invoke(app, ["config", "set", "default_strategy", "agent"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["config", "get", "default_strategy"])
        assert result.exit_code == 0
        assert "agent" in result.output

    def test_set_and_get_json(self, initialized_project, clean_config):
        runner.invoke(app, ["config", "set", "default_scope", "private"])
        result = runner.invoke(app, ["config", "get", "default_scope", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["key"] == "default_scope"
        assert data["value"] == "private"

    def test_invalid_key(self, initialized_project, clean_config):
        result = runner.invoke(app, ["config", "set", "nonexistent", "value"])
        assert result.exit_code == 1

    def test_invalid_value(self, initialized_project, clean_config):
        result = runner.invoke(app, ["config", "set", "default_strategy", "bogus"])
        assert result.exit_code == 1

    def test_get_unset_key(self, initialized_project, clean_config):
        result = runner.invoke(app, ["config", "get", "default_strategy"])
        assert result.exit_code == 0
        assert "not set" in result.output


class TestConfigList:
    def test_list_empty(self, initialized_project, clean_config):
        result = runner.invoke(app, ["config", "list"])
        assert result.exit_code == 0
        assert "No configuration" in result.output

    def test_list_json(self, initialized_project, clean_config):
        runner.invoke(app, ["config", "set", "default_strategy", "theirs"])
        result = runner.invoke(app, ["config", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["default_strategy"] == "theirs"


class TestConfigPullIntegration:
    def test_pull_uses_configured_strategy(self, initialized_project, clean_config):
        """Verify that pull reads the configured default_strategy when --strategy is not passed."""
        runner.invoke(app, ["config", "set", "default_strategy", "theirs"])
        # Pull without --strategy should not error with "invalid strategy"
        # It will fail with "no remote" but should not fail on strategy parsing
        result = runner.invoke(app, ["pull"])
        # The error should be about git/remote, not about strategy
        assert "Invalid strategy" not in result.output
