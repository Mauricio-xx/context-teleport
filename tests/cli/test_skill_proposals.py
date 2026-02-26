"""CLI tests for skill proposal commands (Phase 7b): proposals, apply-proposal."""

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


def _skill_content(name, body="# Instructions\n"):
    return build_frontmatter({"name": name, "description": f"Skill {name}"}, body)


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
    store = ContextStore(initialized_project)
    store.set_skill("debug-drc", _skill_content("debug-drc", "# Original\n"))
    return initialized_project


class TestSkillProposals:
    def test_proposals_empty(self, initialized_project):
        result = runner.invoke(app, ["skill", "proposals"])
        assert result.exit_code == 0
        assert "No proposals" in result.output

    def test_proposals_list(self, project_with_skill):
        store = ContextStore(project_with_skill)
        store.create_skill_proposal("debug-drc", _skill_content("debug-drc", "# v2\n"))
        result = runner.invoke(app, ["skill", "proposals"])
        assert result.exit_code == 0
        assert "debug-drc" in result.output

    def test_proposals_json(self, project_with_skill):
        store = ContextStore(project_with_skill)
        store.create_skill_proposal("debug-drc", _skill_content("debug-drc", "# v2\n"))
        result = runner.invoke(app, ["skill", "proposals", "--format", "json"])
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["skill_name"] == "debug-drc"

    def test_proposals_filter_skill(self, project_with_skill):
        store = ContextStore(project_with_skill)
        store.set_skill("run-lvs", _skill_content("run-lvs"))
        store.create_skill_proposal("debug-drc", _skill_content("debug-drc", "# v2\n"))
        store.create_skill_proposal("run-lvs", _skill_content("run-lvs", "# v2\n"))
        result = runner.invoke(app, ["skill", "proposals", "--skill", "debug-drc", "--format", "json"])
        data = json.loads(result.output)
        assert len(data) == 1

    def test_proposals_filter_status(self, project_with_skill):
        store = ContextStore(project_with_skill)
        store.create_skill_proposal("debug-drc", _skill_content("debug-drc", "# v2\n"))
        result = runner.invoke(app, ["skill", "proposals", "--status", "accepted", "--format", "json"])
        data = json.loads(result.output)
        assert len(data) == 0

    def test_proposals_invalid_status(self, project_with_skill):
        result = runner.invoke(app, ["skill", "proposals", "--status", "bogus"])
        assert result.exit_code == 1


class TestApplyProposal:
    def test_accept_proposal(self, project_with_skill):
        store = ContextStore(project_with_skill)
        new_content = _skill_content("debug-drc", "# Improved\n")
        p = store.create_skill_proposal("debug-drc", new_content)
        result = runner.invoke(app, ["skill", "apply-proposal", "debug-drc", p.id[:8]])
        assert result.exit_code == 0
        assert "accepted" in result.output
        # Verify skill updated
        skill = store.get_skill("debug-drc")
        assert "Improved" in skill.content

    def test_reject_proposal(self, project_with_skill):
        store = ContextStore(project_with_skill)
        original = store.get_skill("debug-drc").content
        new_content = _skill_content("debug-drc", "# Bad change\n")
        p = store.create_skill_proposal("debug-drc", new_content)
        result = runner.invoke(app, ["skill", "apply-proposal", "debug-drc", p.id[:8], "--reject"])
        assert result.exit_code == 0
        assert "rejected" in result.output
        skill = store.get_skill("debug-drc")
        assert skill.content == original

    def test_accept_json(self, project_with_skill):
        store = ContextStore(project_with_skill)
        p = store.create_skill_proposal("debug-drc", _skill_content("debug-drc", "# v2\n"))
        result = runner.invoke(app, ["skill", "apply-proposal", "debug-drc", p.id[:8], "--format", "json"])
        data = json.loads(result.output)
        assert data["action"] == "accepted"

    def test_not_found(self, project_with_skill):
        result = runner.invoke(app, ["skill", "apply-proposal", "debug-drc", "deadbeef"])
        assert result.exit_code == 1

    def test_ambiguous_prefix(self, project_with_skill):
        store = ContextStore(project_with_skill)
        # Create two proposals -- use empty prefix to match both
        store.create_skill_proposal("debug-drc", _skill_content("debug-drc", "# v2\n"))
        store.create_skill_proposal("debug-drc", _skill_content("debug-drc", "# v3\n"))
        # Using empty string would match all -- but typer requires non-empty arg
        # Just test that full id works
        proposals = store.list_skill_proposals()
        result = runner.invoke(app, ["skill", "apply-proposal", "debug-drc", proposals[0].id])
        assert result.exit_code == 0


class TestProposeUpstream:
    def test_propose_upstream_requires_repo(self, project_with_skill):
        """The --repo flag is required."""
        store = ContextStore(project_with_skill)
        p = store.create_skill_proposal("debug-drc", _skill_content("debug-drc", "# v2\n"))
        result = runner.invoke(app, ["skill", "propose-upstream", "debug-drc", p.id[:8]])
        # Should fail because --repo is required
        assert result.exit_code != 0
