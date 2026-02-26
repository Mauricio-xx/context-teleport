"""Tests for MCP skill proposal tools and resources (Phase 7b)."""

from __future__ import annotations

import json

import pytest

from ctx.core.frontmatter import build_frontmatter
from ctx.core.store import ContextStore
from ctx.mcp.server import (
    context_list_skill_proposals,
    context_propose_skill_improvement,
    resource_skill_proposals,
    set_store,
)


def _skill_content(name, body="# Instructions\n"):
    return build_frontmatter({"name": name, "description": f"Skill {name}"}, body)


@pytest.fixture
def store(tmp_path):
    s = ContextStore(tmp_path)
    s.init(project_name="test-mcp-proposals")
    set_store(s)
    yield s
    set_store(None)


@pytest.fixture
def store_with_skill(store):
    store.set_skill("debug-drc", _skill_content("debug-drc", "# Original\n"))
    return store


class TestContextProposeSkillImprovement:
    def test_propose_ok(self, store_with_skill):
        new_content = _skill_content("debug-drc", "# Improved\nBetter instructions\n")
        result = json.loads(context_propose_skill_improvement("debug-drc", new_content, "better flow"))
        assert result["status"] == "ok"
        assert "proposal_id" in result
        assert "diff_summary" in result

    def test_propose_nonexistent_skill(self, store):
        result = json.loads(context_propose_skill_improvement("ghost", "content"))
        assert result["status"] == "error"


class TestContextListSkillProposals:
    def test_empty(self, store_with_skill):
        result = json.loads(context_list_skill_proposals())
        assert result == []

    def test_list_after_create(self, store_with_skill):
        new_content = _skill_content("debug-drc", "# v2\n")
        context_propose_skill_improvement("debug-drc", new_content)
        result = json.loads(context_list_skill_proposals())
        assert len(result) == 1
        assert result[0]["skill_name"] == "debug-drc"
        assert result[0]["status"] == "pending"

    def test_filter_by_skill(self, store):
        store.set_skill("a", _skill_content("a"))
        store.set_skill("b", _skill_content("b"))
        context_propose_skill_improvement("a", _skill_content("a", "# new\n"))
        context_propose_skill_improvement("b", _skill_content("b", "# new\n"))
        result = json.loads(context_list_skill_proposals(skill_name="a"))
        assert len(result) == 1

    def test_filter_by_status(self, store_with_skill):
        new_content = _skill_content("debug-drc", "# v2\n")
        context_propose_skill_improvement("debug-drc", new_content)
        result = json.loads(context_list_skill_proposals(status="pending"))
        assert len(result) == 1
        result2 = json.loads(context_list_skill_proposals(status="accepted"))
        assert len(result2) == 0

    def test_invalid_status(self, store_with_skill):
        result = json.loads(context_list_skill_proposals(status="bogus"))
        assert result["status"] == "error"


class TestResourceSkillProposals:
    def test_empty(self, store_with_skill):
        result = json.loads(resource_skill_proposals("debug-drc"))
        assert result == []

    def test_with_proposals(self, store_with_skill):
        new_content = _skill_content("debug-drc", "# v2\n")
        context_propose_skill_improvement("debug-drc", new_content)
        result = json.loads(resource_skill_proposals("debug-drc"))
        assert len(result) == 1

    def test_nonexistent_skill(self, store):
        result = json.loads(resource_skill_proposals("ghost"))
        assert "error" in result
