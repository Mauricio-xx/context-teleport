"""Tests for git sync operations."""

import git
import pytest

from ctx.core.store import ContextStore
from ctx.sync.git_sync import GitSync, GitSyncError


class TestGitSync:
    def test_init_requires_git_repo(self, tmp_path):
        with pytest.raises(GitSyncError):
            GitSync(tmp_path)

    def test_push_nothing(self, store):
        # Commit the initial store
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        gs = GitSync(store.root)
        result = gs.push()
        assert result["status"] == "nothing_to_push"

    def test_push_with_changes(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        # Make a change
        store.set_knowledge("arch", "New architecture info")

        gs = GitSync(store.root)
        result = gs.push()
        assert result["status"] == "committed"
        assert "ctx:" in result["commit_message"]

    def test_push_custom_message(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        store.set_knowledge("test", "value")

        gs = GitSync(store.root)
        result = gs.push(message="custom message")
        assert result["commit_message"] == "custom message"

    def test_diff_no_changes(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        gs = GitSync(store.root)
        result = gs.diff()
        assert result["diff"] == ""

    def test_log(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        store.set_knowledge("test", "data")
        gs = GitSync(store.root)
        gs.push(message="ctx: add test knowledge")

        result = gs.log(oneline=True)
        assert "ctx: add test knowledge" in result["log"]

    def test_auto_message_knowledge(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        store.set_knowledge("architecture", "Microservices")

        gs = GitSync(store.root)
        msg = gs._auto_message()
        assert "architecture" in msg
        assert "ctx:" in msg

    def test_auto_message_decision(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        store.add_decision(title="Use Docker")

        gs = GitSync(store.root)
        msg = gs._auto_message()
        assert "decision" in msg
