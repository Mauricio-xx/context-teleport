"""Tests for CLI activity commands: list, check-in, check-out."""

from __future__ import annotations

import json
import os

import pytest
from typer.testing import CliRunner

from ctx.cli.main import app
from ctx.core.store import ContextStore

runner = CliRunner()


@pytest.fixture
def store(tmp_git_repo):
    orig = os.getcwd()
    os.chdir(tmp_git_repo)
    s = ContextStore(tmp_git_repo)
    s.init(project_name="cli-activity-test")
    yield s
    os.chdir(orig)


class TestActivityList:
    def test_list_empty(self, store):
        result = runner.invoke(app, ["activity", "list"])
        assert result.exit_code == 0
        assert "No active team members" in result.output

    def test_list_with_entries(self, store):
        store.check_in(task="DRC fix", member="alice", agent="claude-code")
        store.check_in(task="LVS check", member="bob", agent="cursor")
        result = runner.invoke(app, ["activity", "list"])
        assert result.exit_code == 0
        assert "alice" in result.output
        assert "bob" in result.output

    def test_list_json(self, store):
        store.check_in(task="DRC fix", member="alice", agent="claude-code", issue_ref="#42")
        result = runner.invoke(app, ["activity", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["member"] == "alice"
        assert data[0]["issue_ref"] == "#42"


class TestActivityCheckIn:
    def test_check_in_basic(self, store):
        result = runner.invoke(app, ["activity", "check-in", "Fixing DRC violations"])
        assert result.exit_code == 0
        assert "Checked in" in result.output
        entries = store.list_activity()
        assert len(entries) == 1

    def test_check_in_with_issue(self, store):
        result = runner.invoke(app, ["activity", "check-in", "Fix DRC", "--issue", "#42"])
        assert result.exit_code == 0
        entries = store.list_activity()
        assert entries[0].issue_ref == "#42"

    def test_check_in_json(self, store):
        result = runner.invoke(app, ["activity", "check-in", "Working", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "checked_in"


class TestActivityCheckOut:
    def test_check_out_existing(self, store):
        store.check_in(task="Working")
        result = runner.invoke(app, ["activity", "check-out"])
        assert result.exit_code == 0
        assert "Checked out" in result.output
        assert store.list_activity() == []

    def test_check_out_missing(self, store):
        result = runner.invoke(app, ["activity", "check-out"])
        assert result.exit_code == 1

    def test_check_out_json_existing(self, store):
        store.check_in(task="Working")
        result = runner.invoke(app, ["activity", "check-out", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "checked_out"

    def test_check_out_json_missing(self, store):
        result = runner.invoke(app, ["activity", "check-out", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "not_found"
