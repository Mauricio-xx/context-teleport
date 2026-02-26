"""Tests for skill usage tracking and feedback (Phase 7a)."""

from __future__ import annotations

import pytest

from ctx.core.frontmatter import build_frontmatter
from ctx.core.schema import SkillFeedback, SkillStats, SkillUsageEvent
from ctx.core.store import ContextStore, StoreError


@pytest.fixture
def store(tmp_path):
    s = ContextStore(tmp_path)
    s.init(project_name="test-tracking")
    return s


@pytest.fixture
def store_with_skill(store):
    content = build_frontmatter({"name": "debug-drc", "description": "DRC debugging"}, "# debug-drc\n")
    store.set_skill("debug-drc", content)
    return store


class TestRecordSkillUsage:
    def test_record_creates_event(self, store_with_skill):
        event = store_with_skill.record_skill_usage("debug-drc", agent="claude")
        assert isinstance(event, SkillUsageEvent)
        assert event.agent == "claude"
        assert event.id

    def test_record_appends_to_ndjson(self, store_with_skill):
        store_with_skill.record_skill_usage("debug-drc", agent="a1")
        store_with_skill.record_skill_usage("debug-drc", agent="a2")
        path = store_with_skill._skill_usage_path("debug-drc")
        lines = [ln for ln in path.read_text().strip().split("\n") if ln.strip()]
        assert len(lines) == 2

    def test_record_with_session_id(self, store_with_skill):
        event = store_with_skill.record_skill_usage("debug-drc", session_id="sess-1")
        assert event.session_id == "sess-1"

    def test_record_nonexistent_skill_raises(self, store):
        with pytest.raises(StoreError, match="not found"):
            store.record_skill_usage("nonexistent")


class TestAddSkillFeedback:
    def test_add_feedback(self, store_with_skill):
        fb = store_with_skill.add_skill_feedback("debug-drc", 5, comment="great", agent="claude")
        assert isinstance(fb, SkillFeedback)
        assert fb.rating == 5
        assert fb.comment == "great"

    def test_add_feedback_appends(self, store_with_skill):
        store_with_skill.add_skill_feedback("debug-drc", 4)
        store_with_skill.add_skill_feedback("debug-drc", 2)
        path = store_with_skill._skill_feedback_path("debug-drc")
        lines = [ln for ln in path.read_text().strip().split("\n") if ln.strip()]
        assert len(lines) == 2

    def test_invalid_rating_low(self, store_with_skill):
        with pytest.raises(StoreError, match="1-5"):
            store_with_skill.add_skill_feedback("debug-drc", 0)

    def test_invalid_rating_high(self, store_with_skill):
        with pytest.raises(StoreError, match="1-5"):
            store_with_skill.add_skill_feedback("debug-drc", 6)

    def test_feedback_nonexistent_skill(self, store):
        with pytest.raises(StoreError, match="not found"):
            store.add_skill_feedback("ghost", 3)


class TestListSkillFeedback:
    def test_empty_feedback(self, store_with_skill):
        assert store_with_skill.list_skill_feedback("debug-drc") == []

    def test_returns_all_entries(self, store_with_skill):
        store_with_skill.add_skill_feedback("debug-drc", 5, agent="a")
        store_with_skill.add_skill_feedback("debug-drc", 2, agent="b")
        feedback = store_with_skill.list_skill_feedback("debug-drc")
        assert len(feedback) == 2
        assert feedback[0].agent == "a"
        assert feedback[1].agent == "b"


class TestGetSkillStats:
    def test_empty_stats(self, store_with_skill):
        stats = store_with_skill.get_skill_stats("debug-drc")
        assert isinstance(stats, SkillStats)
        assert stats.usage_count == 0
        assert stats.avg_rating == 0.0
        assert stats.rating_count == 0
        assert stats.last_used is None
        assert not stats.needs_attention

    def test_usage_count(self, store_with_skill):
        store_with_skill.record_skill_usage("debug-drc")
        store_with_skill.record_skill_usage("debug-drc")
        store_with_skill.record_skill_usage("debug-drc")
        stats = store_with_skill.get_skill_stats("debug-drc")
        assert stats.usage_count == 3
        assert stats.last_used is not None

    def test_avg_rating(self, store_with_skill):
        store_with_skill.add_skill_feedback("debug-drc", 4)
        store_with_skill.add_skill_feedback("debug-drc", 2)
        stats = store_with_skill.get_skill_stats("debug-drc")
        assert stats.avg_rating == 3.0
        assert stats.rating_count == 2

    def test_needs_attention(self, store_with_skill):
        store_with_skill.add_skill_feedback("debug-drc", 1)
        store_with_skill.add_skill_feedback("debug-drc", 2)
        stats = store_with_skill.get_skill_stats("debug-drc")
        assert stats.needs_attention is True

    def test_no_attention_with_one_rating(self, store_with_skill):
        store_with_skill.add_skill_feedback("debug-drc", 1)
        stats = store_with_skill.get_skill_stats("debug-drc")
        assert stats.needs_attention is False

    def test_no_attention_with_high_rating(self, store_with_skill):
        store_with_skill.add_skill_feedback("debug-drc", 4)
        store_with_skill.add_skill_feedback("debug-drc", 5)
        stats = store_with_skill.get_skill_stats("debug-drc")
        assert stats.needs_attention is False


class TestListSkillStats:
    def test_empty_store(self, store):
        assert store.list_skill_stats() == []

    def test_multiple_skills(self, store):
        for name in ["a", "b", "c"]:
            content = build_frontmatter({"name": name, "description": f"Skill {name}"}, f"# {name}\n")
            store.set_skill(name, content)
        store.record_skill_usage("a")
        store.record_skill_usage("b")
        store.record_skill_usage("b")
        stats = store.list_skill_stats()
        assert len(stats) == 3
        by_name = {s.skill_name: s for s in stats}
        assert by_name["a"].usage_count == 1
        assert by_name["b"].usage_count == 2
        assert by_name["c"].usage_count == 0


class TestSkillRemovalCleansTracking:
    def test_rm_skill_removes_tracking_data(self, store_with_skill):
        store_with_skill.record_skill_usage("debug-drc")
        store_with_skill.add_skill_feedback("debug-drc", 4)
        store_with_skill.rm_skill("debug-drc")
        assert not store_with_skill._skill_usage_path("debug-drc").exists()
        assert not store_with_skill._skill_feedback_path("debug-drc").exists()


class TestSessionSummarySkillsUsed:
    def test_skills_used_default(self):
        from ctx.core.schema import SessionSummary

        s = SessionSummary()
        assert s.skills_used == []

    def test_skills_used_populated(self):
        from ctx.core.schema import SessionSummary

        s = SessionSummary(skills_used=["debug-drc", "run-lvs"])
        assert s.skills_used == ["debug-drc", "run-lvs"]
