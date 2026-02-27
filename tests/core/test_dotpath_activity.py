"""Tests for activity in dotpath resolution (read-only)."""

from __future__ import annotations

import pytest

from ctx.core.dotpath import resolve_dotpath


class TestDotpathActivity:
    def test_resolve_all_activity(self, store):
        store.check_in(task="DRC fix", member="alice")
        store.check_in(task="LVS check", member="bob")
        result = resolve_dotpath(store, "activity")
        assert isinstance(result, list)
        assert len(result) == 2
        members = {r["member"] for r in result}
        assert members == {"alice", "bob"}

    def test_resolve_single_member(self, store):
        store.check_in(task="DRC fix", member="alice", agent="claude-code")
        result = resolve_dotpath(store, "activity.alice")
        assert result is not None
        assert result["member"] == "alice"
        assert result["task"] == "DRC fix"

    def test_resolve_missing_member(self, store):
        result = resolve_dotpath(store, "activity.nobody")
        assert result is None
