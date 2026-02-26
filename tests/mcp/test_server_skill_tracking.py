"""Tests for MCP skill tracking tools and resources (Phase 7a)."""

from __future__ import annotations

import json

import pytest

from ctx.core.frontmatter import build_frontmatter
from ctx.core.store import ContextStore
from ctx.mcp.server import (
    context_rate_skill,
    context_report_skill_usage,
    resource_skill_feedback,
    resource_skills_stats,
    set_store,
)


@pytest.fixture
def store(tmp_path):
    s = ContextStore(tmp_path)
    s.init(project_name="test-mcp-tracking")
    set_store(s)
    yield s
    set_store(None)


@pytest.fixture
def store_with_skill(store):
    content = build_frontmatter({"name": "run-lvs", "description": "Run LVS"}, "# run-lvs\n")
    store.set_skill("run-lvs", content)
    return store


class TestContextReportSkillUsage:
    def test_report_usage_ok(self, store_with_skill):
        result = json.loads(context_report_skill_usage("run-lvs"))
        assert result["status"] == "ok"
        assert "event_id" in result

    def test_report_usage_nonexistent(self, store):
        result = json.loads(context_report_skill_usage("ghost"))
        assert result["status"] == "error"

    def test_multiple_usages_counted(self, store_with_skill):
        context_report_skill_usage("run-lvs")
        context_report_skill_usage("run-lvs")
        stats_json = json.loads(resource_skills_stats())
        stats = {s["skill_name"]: s for s in stats_json}
        assert stats["run-lvs"]["usage_count"] == 2


class TestContextRateSkill:
    def test_rate_ok(self, store_with_skill):
        result = json.loads(context_rate_skill("run-lvs", 5, "excellent"))
        assert result["status"] == "ok"
        assert "feedback_id" in result

    def test_rate_invalid_rating(self, store_with_skill):
        result = json.loads(context_rate_skill("run-lvs", 0))
        assert result["status"] == "error"

    def test_rate_nonexistent_skill(self, store):
        result = json.loads(context_rate_skill("ghost", 3))
        assert result["status"] == "error"


class TestResourceSkillsStats:
    def test_empty_stats(self, store_with_skill):
        result = json.loads(resource_skills_stats())
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["skill_name"] == "run-lvs"
        assert result[0]["usage_count"] == 0

    def test_stats_with_data(self, store_with_skill):
        context_report_skill_usage("run-lvs")
        context_rate_skill("run-lvs", 4)
        context_rate_skill("run-lvs", 2)
        result = json.loads(resource_skills_stats())
        stats = result[0]
        assert stats["usage_count"] == 1
        assert stats["avg_rating"] == 3.0
        assert stats["rating_count"] == 2


class TestResourceSkillFeedback:
    def test_empty_feedback(self, store_with_skill):
        result = json.loads(resource_skill_feedback("run-lvs"))
        assert result == []

    def test_feedback_entries(self, store_with_skill):
        context_rate_skill("run-lvs", 5, "great")
        context_rate_skill("run-lvs", 2, "needs work")
        result = json.loads(resource_skill_feedback("run-lvs"))
        assert len(result) == 2

    def test_feedback_nonexistent_skill(self, store):
        result = json.loads(resource_skill_feedback("ghost"))
        assert "error" in result
