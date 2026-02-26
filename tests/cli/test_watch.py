"""Tests for the ctx watch command."""

from __future__ import annotations

import os
from unittest.mock import patch

import git
import pytest
from typer.testing import CliRunner

from ctx.cli.main import app
from ctx.cli.watch_cmd import _try_push
from ctx.core.store import ContextStore
from ctx.sync.git_sync import GitSync, GitSyncError
from ctx.utils.paths import STORE_DIR

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path):
    """Create a git repo with initialized context store."""
    repo = git.Repo.init(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial")

    store = ContextStore(tmp_path)
    store.init(project_name="watch-test")
    repo.index.add([STORE_DIR])
    repo.index.commit("init context store")

    original = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original)


class TestWatchHelp:
    def test_watch_help(self):
        result = runner.invoke(app, ["watch", "--help"])
        assert result.exit_code == 0
        assert "Watch the context store" in result.output
        assert "--debounce" in result.output
        assert "--interval" in result.output
        assert "--no-push" in result.output


class TestTryPush:
    def test_try_push_with_changes(self, project_dir):
        gs = GitSync(project_dir)
        store = ContextStore(project_dir)
        store.set_knowledge("test", "content")

        pushed = _try_push(gs, no_push=False)
        assert pushed is True

    def test_try_push_no_changes(self, project_dir):
        gs = GitSync(project_dir)
        pushed = _try_push(gs, no_push=False)
        assert pushed is False

    def test_try_push_error_handling(self, project_dir):
        gs = GitSync(project_dir)
        with patch.object(gs, "_has_changes", side_effect=GitSyncError("boom")):
            pushed = _try_push(gs, no_push=False)
            assert pushed is False


class TestNoPushFlag:
    def test_no_push_does_not_call_push(self, project_dir):
        """When no_push=True, _try_push calls commit() instead of push()."""
        gs = GitSync(project_dir)
        store = ContextStore(project_dir)
        store.set_knowledge("nopush-test", "content")

        with patch.object(gs, "push") as mock_push, \
             patch.object(gs, "commit", return_value={"status": "committed"}) as mock_commit:
            result = _try_push(gs, no_push=True)
            assert result is True
            mock_push.assert_not_called()
            mock_commit.assert_called_once()

    def test_push_called_when_flag_false(self, project_dir):
        """When no_push=False, _try_push calls push() as normal."""
        gs = GitSync(project_dir)
        store = ContextStore(project_dir)
        store.set_knowledge("push-test", "content")

        with patch.object(gs, "push", return_value={"status": "pushed"}) as mock_push, \
             patch.object(gs, "commit") as mock_commit:
            result = _try_push(gs, no_push=False)
            assert result is True
            mock_commit.assert_not_called()
            mock_push.assert_called_once()


class TestWatchRequiresInit:
    def test_watch_requires_init(self, tmp_path):
        """Watch should fail if no context store is initialized."""
        repo = git.Repo.init(tmp_path)
        readme = tmp_path / "README.md"
        readme.write_text("# Test\n")
        repo.index.add(["README.md"])
        repo.index.commit("initial")

        original = os.getcwd()
        os.chdir(tmp_path)
        try:
            result = runner.invoke(app, ["watch"])
            assert result.exit_code != 0
        finally:
            os.chdir(original)
