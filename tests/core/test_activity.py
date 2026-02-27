"""Tests for team activity board: check_in, check_out, list, get, stale detection, summary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from ctx.core.schema import ACTIVITY_STALE_HOURS, ActivityEntry
from ctx.core.store import ContextStore


class TestCheckIn:
    def test_check_in_creates_file(self, store):
        entry = store.check_in(task="Fixing DRC violations", agent="claude-code")
        assert entry.task == "Fixing DRC violations"
        assert entry.agent == "claude-code"
        assert entry.status == "active"
        assert (store.activity_dir() / f"{entry.member}.json").is_file()

    def test_check_in_with_issue_ref(self, store):
        entry = store.check_in(task="Fixing DRC", issue_ref="#42")
        assert entry.issue_ref == "#42"

    def test_check_in_lazy_dir_creation(self, store):
        assert not store.activity_dir().is_dir()
        store.check_in(task="Working")
        assert store.activity_dir().is_dir()

    def test_check_in_overwrites_on_recheck(self, store):
        store.check_in(task="Task v1", member="alice")
        store.check_in(task="Task v2", member="alice")
        entry = store.get_activity("alice")
        assert entry.task == "Task v2"

    def test_check_in_member_defaults_to_username(self, store):
        with patch("ctx.core.store.get_username", return_value="testuser"):
            entry = store.check_in(task="Working")
        assert entry.member == "testuser"

    def test_check_in_machine_defaults(self, store):
        with patch("ctx.core.store.get_machine_name", return_value="laptop-dev"):
            entry = store.check_in(task="Working", member="alice")
        assert entry.machine == "laptop-dev"


class TestCheckOut:
    def test_check_out_removes_file(self, store):
        store.check_in(task="Working", member="alice")
        assert store.check_out(member="alice") is True
        assert store.get_activity("alice") is None

    def test_check_out_missing_returns_false(self, store):
        assert store.check_out(member="nobody") is False

    def test_check_out_defaults_to_current_user(self, store):
        with patch("ctx.core.store.get_username", return_value="testuser"):
            store.check_in(task="Working")
            assert store.check_out() is True


class TestListActivity:
    def test_list_empty(self, store):
        assert store.list_activity() == []

    def test_list_returns_all(self, store):
        store.check_in(task="DRC fix", member="alice")
        store.check_in(task="LVS check", member="bob")
        entries = store.list_activity()
        assert len(entries) == 2
        members = {e.member for e in entries}
        assert members == {"alice", "bob"}


class TestGetActivity:
    def test_get_existing(self, store):
        store.check_in(task="Working", member="alice", agent="cursor")
        entry = store.get_activity("alice")
        assert entry is not None
        assert entry.task == "Working"
        assert entry.agent == "cursor"

    def test_get_missing(self, store):
        assert store.get_activity("nobody") is None


class TestStaleDetection:
    def test_fresh_entry_not_stale(self, store):
        entry = store.check_in(task="Working", member="alice")
        assert store.is_stale(entry) is False

    def test_old_entry_is_stale(self, store):
        entry = ActivityEntry(
            member="alice",
            task="Old work",
            updated_at=datetime.now(timezone.utc) - timedelta(hours=ACTIVITY_STALE_HOURS + 1),
        )
        assert store.is_stale(entry) is True

    def test_boundary_not_stale(self, store):
        entry = ActivityEntry(
            member="alice",
            task="Recent",
            updated_at=datetime.now(timezone.utc) - timedelta(hours=ACTIVITY_STALE_HOURS - 1),
        )
        assert store.is_stale(entry) is False


class TestSummaryIncludesActivity:
    def test_summary_with_activity(self, store):
        store.check_in(task="DRC fix", member="alice")
        store.check_in(task="LVS check", member="bob")
        s = store.summary()
        assert s["active_members"] == 2
        assert "alice" in s["active_member_names"]
        assert "bob" in s["active_member_names"]

    def test_summary_no_activity(self, store):
        s = store.summary()
        assert s["active_members"] == 0
        assert s["active_member_names"] == []
