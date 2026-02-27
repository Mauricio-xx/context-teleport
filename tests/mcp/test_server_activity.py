"""Tests for MCP server activity tools, resource, instructions, and onboarding."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from ctx.core.schema import ACTIVITY_STALE_HOURS, ActivityEntry
from ctx.core.store import ContextStore
from ctx.mcp.server import (
    _generate_instructions,
    context_check_in,
    context_check_out,
    context_onboarding,
    resource_activity,
    set_store,
)


@pytest.fixture
def store(tmp_path):
    s = ContextStore(tmp_path)
    s.init(project_name="test-activity")
    set_store(s)
    yield s
    set_store(None)


class TestCheckInTool:
    def test_check_in_creates_entry(self, store):
        result = json.loads(context_check_in("Fixing DRC violations", issue_ref="#42"))
        assert result["status"] == "ok"
        assert result["task"] == "Fixing DRC violations"
        entries = store.list_activity()
        assert len(entries) == 1
        assert entries[0].issue_ref == "#42"

    def test_check_in_overwrites(self, store):
        context_check_in("Task v1")
        context_check_in("Task v2")
        entries = store.list_activity()
        assert len(entries) == 1
        assert entries[0].task == "Task v2"


class TestCheckOutTool:
    def test_check_out_removes_entry(self, store):
        context_check_in("Working")
        result = json.loads(context_check_out())
        assert result["status"] == "checked_out"
        assert store.list_activity() == []

    def test_check_out_not_found(self, store):
        result = json.loads(context_check_out())
        assert result["status"] == "not_found"


class TestActivityResource:
    def test_resource_empty(self, store):
        result = json.loads(resource_activity())
        assert result == []

    def test_resource_with_entries(self, store):
        store.check_in(task="DRC fix", member="alice", agent="claude-code", issue_ref="#42")
        result = json.loads(resource_activity())
        assert len(result) == 1
        assert result[0]["member"] == "alice"
        assert result[0]["task"] == "DRC fix"
        assert result[0]["stale"] is False

    def test_resource_stale_flag(self, store):
        # Write a stale entry directly
        adir = store.activity_dir()
        adir.mkdir(parents=True, exist_ok=True)
        old_time = datetime.now(timezone.utc) - timedelta(hours=ACTIVITY_STALE_HOURS + 1)
        entry = ActivityEntry(member="old-user", task="Old work", updated_at=old_time)
        store._write_json(adir / "old-user.json", entry)

        result = json.loads(resource_activity())
        assert len(result) == 1
        assert result[0]["stale"] is True


class TestActivityInInstructions:
    def test_instructions_include_activity(self, store):
        store.check_in(task="DRC fix", member="alice", agent="claude-code", issue_ref="#42")
        text = _generate_instructions()
        assert "Team activity" in text
        assert "alice" in text
        assert "DRC fix" in text
        assert "#42" in text

    def test_instructions_no_activity(self, store):
        text = _generate_instructions()
        assert "Team activity" not in text


class TestActivityInOnboarding:
    def test_onboarding_includes_activity(self, store):
        store.check_in(task="DRC fix", member="alice", agent="claude-code", issue_ref="#42")
        text = context_onboarding()
        assert "## Team Activity" in text
        assert "**alice**" in text
        assert "DRC fix" in text
        assert "[#42]" in text
        assert "via claude-code" in text

    def test_onboarding_activity_before_conventions(self, store):
        store.check_in(task="Working", member="alice", agent="test")
        store.set_convention("git", "Use branches.")
        text = context_onboarding()
        act_idx = text.index("## Team Activity")
        conv_idx = text.index("## Team Conventions")
        assert act_idx < conv_idx

    def test_onboarding_no_activity(self, store):
        text = context_onboarding()
        assert "Team Activity" not in text

    def test_onboarding_stale_marker(self, store):
        """Stale entries should be omitted from full listing, with a summary note."""
        adir = store.activity_dir()
        adir.mkdir(parents=True, exist_ok=True)
        old_time = datetime.now(timezone.utc) - timedelta(hours=ACTIVITY_STALE_HOURS + 1)
        entry = ActivityEntry(member="stale-user", task="Old work", agent="test", updated_at=old_time)
        store._write_json(adir / "stale-user.json", entry)

        text = context_onboarding()
        # Stale entry should NOT appear as a full entry
        assert "**stale-user**" not in text
        # But the section and summary note should be present
        assert "## Team Activity" in text
        assert "stale entries omitted" in text

    def test_onboarding_filters_stale_keeps_active(self, store):
        """Only active entries shown in full; stale entries counted in summary."""
        # Active entry
        store.check_in(task="Active work", member="alice", agent="claude-code")

        # Stale entry
        adir = store.activity_dir()
        old_time = datetime.now(timezone.utc) - timedelta(hours=ACTIVITY_STALE_HOURS + 1)
        stale = ActivityEntry(member="bob", task="Old work", agent="test", updated_at=old_time)
        store._write_json(adir / "bob.json", stale)

        text = context_onboarding()
        assert "## Team Activity" in text
        # Active entry shows in full
        assert "**alice**" in text
        assert "Active work" in text
        # Stale entry omitted from full listing
        assert "**bob**" not in text
        assert "1 stale entries omitted" in text
