"""CLI tests for skill tracking commands (Phase 7a): stats, feedback, review."""

from __future__ import annotations

import json
import os

import git
import pytest
from typer.testing import CliRunner

from ctx.cli.main import app
from ctx.core.frontmatter import build_frontmatter
from ctx.core.store import ContextStore

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path):
    repo = git.Repo.init(tmp_path)
    (tmp_path / "README.md").write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    original = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original)


@pytest.fixture
def initialized_project(project_dir):
    runner.invoke(app, ["init", "--name", "test-project"])
    return project_dir


@pytest.fixture
def project_with_skill(initialized_project):
    content = build_frontmatter(
        {"name": "debug-drc", "description": "Debug DRC issues"}, "# debug-drc\n"
    )
    store = ContextStore(initialized_project)
    store.set_skill("debug-drc", content)
    return initialized_project


class TestSkillStats:
    def test_stats_no_skills(self, initialized_project):
        result = runner.invoke(app, ["skill", "stats"])
        assert result.exit_code == 0
        assert "No skills" in result.output

    def test_stats_with_skill(self, project_with_skill):
        result = runner.invoke(app, ["skill", "stats"])
        assert result.exit_code == 0
        assert "debug-drc" in result.output

    def test_stats_json(self, project_with_skill):
        result = runner.invoke(app, ["skill", "stats", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["skill_name"] == "debug-drc"

    def test_stats_with_usage(self, project_with_skill):
        store = ContextStore(project_with_skill)
        store.record_skill_usage("debug-drc")
        store.record_skill_usage("debug-drc")
        result = runner.invoke(app, ["skill", "stats", "--format", "json"])
        data = json.loads(result.output)
        assert data[0]["usage_count"] == 2

    def test_stats_sort_usage(self, project_with_skill):
        result = runner.invoke(app, ["skill", "stats", "--sort", "usage"])
        assert result.exit_code == 0

    def test_stats_sort_rating(self, project_with_skill):
        result = runner.invoke(app, ["skill", "stats", "--sort", "rating"])
        assert result.exit_code == 0


class TestSkillFeedback:
    def test_feedback_not_found(self, initialized_project):
        result = runner.invoke(app, ["skill", "feedback", "ghost"])
        assert result.exit_code == 1

    def test_feedback_empty(self, project_with_skill):
        result = runner.invoke(app, ["skill", "feedback", "debug-drc"])
        assert result.exit_code == 0
        assert "No feedback" in result.output

    def test_feedback_with_entries(self, project_with_skill):
        store = ContextStore(project_with_skill)
        store.add_skill_feedback("debug-drc", 5, comment="solid", agent="claude")
        result = runner.invoke(app, ["skill", "feedback", "debug-drc"])
        assert result.exit_code == 0
        assert "claude" in result.output

    def test_feedback_json(self, project_with_skill):
        store = ContextStore(project_with_skill)
        store.add_skill_feedback("debug-drc", 4, agent="test")
        result = runner.invoke(app, ["skill", "feedback", "debug-drc", "--format", "json"])
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["rating"] == 4


class TestSkillReview:
    def test_review_nothing(self, initialized_project):
        result = runner.invoke(app, ["skill", "review"])
        assert result.exit_code == 0
        assert "No skills need attention" in result.output

    def test_review_with_attention(self, project_with_skill):
        store = ContextStore(project_with_skill)
        store.add_skill_feedback("debug-drc", 1)
        store.add_skill_feedback("debug-drc", 2)
        result = runner.invoke(app, ["skill", "review"])
        assert result.exit_code == 0
        assert "debug-drc" in result.output

    def test_review_json(self, project_with_skill):
        store = ContextStore(project_with_skill)
        store.add_skill_feedback("debug-drc", 1)
        store.add_skill_feedback("debug-drc", 2)
        result = runner.invoke(app, ["skill", "review", "--format", "json"])
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["skill"]["needs_attention"] is True
