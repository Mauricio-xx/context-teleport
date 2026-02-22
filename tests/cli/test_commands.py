"""Integration tests for CLI commands via typer.testing.CliRunner."""

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


class TestInit:
    def test_init_success(self, project_dir):
        result = runner.invoke(app, ["init", "--name", "my-proj"])
        assert result.exit_code == 0
        assert "my-proj" in result.output

    def test_init_twice_fails(self, initialized_project):
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 1

    def test_init_json(self, project_dir):
        result = runner.invoke(app, ["init", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "project" in data


class TestStatus:
    def test_status(self, initialized_project):
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "test-project" in result.output

    def test_status_json(self, initialized_project):
        result = runner.invoke(app, ["status", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["project"] == "test-project"


class TestKnowledge:
    def test_set_and_get(self, initialized_project):
        result = runner.invoke(app, ["knowledge", "set", "arch", "Hexagonal"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["knowledge", "get", "arch", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["content"] == "Hexagonal"

    def test_list(self, initialized_project):
        runner.invoke(app, ["knowledge", "set", "a", "aaa"])
        runner.invoke(app, ["knowledge", "set", "b", "bbb"])
        result = runner.invoke(app, ["knowledge", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2

    def test_rm(self, initialized_project):
        runner.invoke(app, ["knowledge", "set", "temp", "data"])
        result = runner.invoke(app, ["knowledge", "rm", "temp"])
        assert result.exit_code == 0

        result = runner.invoke(app, ["knowledge", "get", "temp"])
        assert result.exit_code == 1

    def test_search(self, initialized_project):
        runner.invoke(app, ["knowledge", "set", "arch", "Hexagonal architecture pattern"])
        result = runner.invoke(app, ["knowledge", "search", "hexagonal", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) > 0


class TestDecision:
    def test_add_and_list(self, initialized_project):
        result = runner.invoke(
            app, ["decision", "add", "Use PostgreSQL"], input="## Context\nNeed DB\n\n## Decision\nPostgreSQL\n\n## Consequences\nManaged DB\n"
        )
        assert result.exit_code == 0
        assert "0001" in result.output

        result = runner.invoke(app, ["decision", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["title"] == "Use PostgreSQL"

    def test_get(self, initialized_project):
        runner.invoke(
            app, ["decision", "add", "Test Decision"], input="## Context\nTest\n"
        )
        result = runner.invoke(app, ["decision", "get", "1", "--format", "json"])
        assert result.exit_code == 0


class TestState:
    def test_set_and_show(self, initialized_project):
        runner.invoke(app, ["state", "set", "current_task", "Testing"])
        result = runner.invoke(app, ["state", "show", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["current_task"] == "Testing"

    def test_clear(self, initialized_project):
        runner.invoke(app, ["state", "set", "current_task", "Doing stuff"])
        runner.invoke(app, ["state", "clear"])
        result = runner.invoke(app, ["state", "show", "--format", "json"])
        data = json.loads(result.output)
        assert data["current_task"] == ""


class TestAgentCommands:
    def test_get_knowledge(self, initialized_project):
        runner.invoke(app, ["knowledge", "set", "arch", "Hexagonal"])
        result = runner.invoke(app, ["get", "knowledge.arch"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["value"] == "Hexagonal"

    def test_set_knowledge(self, initialized_project):
        result = runner.invoke(app, ["set", "knowledge.mykey", "myvalue"])
        assert result.exit_code == 0
        result = runner.invoke(app, ["get", "knowledge.mykey"])
        data = json.loads(result.output)
        assert data["value"] == "myvalue"

    def test_summary(self, initialized_project):
        runner.invoke(app, ["knowledge", "set", "arch", "Hexagonal"])
        result = runner.invoke(app, ["summary"])
        assert result.exit_code == 0
        assert "test-project" in result.output

    def test_search(self, initialized_project):
        runner.invoke(app, ["knowledge", "set", "arch", "Hexagonal architecture"])
        result = runner.invoke(app, ["search", "hexagonal", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) > 0


class TestSync:
    def test_push_no_changes(self, initialized_project):
        # First commit the store
        repo = git.Repo(initialized_project)
        repo.index.add([".context-teleport"])
        repo.index.commit("init ctx")

        result = runner.invoke(app, ["push"])
        assert result.exit_code == 0
        assert "No context changes" in result.output

    def test_log(self, initialized_project):
        repo = git.Repo(initialized_project)
        repo.index.add([".context-teleport"])
        repo.index.commit("init ctx")

        result = runner.invoke(app, ["log", "--oneline"])
        assert result.exit_code == 0
