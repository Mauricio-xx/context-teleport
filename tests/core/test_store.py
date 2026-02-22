"""Tests for ContextStore."""

import pytest

from ctx.core.schema import ActiveState, SessionSummary
from ctx.core.store import ContextStore, StoreError


class TestInit:
    def test_init_creates_structure(self, tmp_git_repo):
        store = ContextStore(tmp_git_repo)
        manifest = store.init(project_name="my-project")
        assert store.initialized
        assert manifest.project.name == "my-project"
        assert (store.store_dir / "manifest.json").is_file()
        assert (store.store_dir / "knowledge").is_dir()
        assert (store.store_dir / "knowledge" / "decisions").is_dir()
        assert (store.store_dir / "state").is_dir()
        assert (store.store_dir / "preferences").is_dir()
        assert (store.store_dir / "history").is_dir()
        assert (store.store_dir / ".gitignore").is_file()

    def test_init_twice_raises(self, store):
        with pytest.raises(StoreError, match="already initialized"):
            store.init()

    def test_default_project_name(self, tmp_git_repo):
        store = ContextStore(tmp_git_repo)
        manifest = store.init()
        assert manifest.project.name == tmp_git_repo.name


class TestKnowledge:
    def test_set_and_get(self, store):
        store.set_knowledge("arch", "Hexagonal architecture")
        entry = store.get_knowledge("arch")
        assert entry is not None
        assert entry.content == "Hexagonal architecture"
        assert entry.key == "arch"

    def test_get_nonexistent(self, store):
        assert store.get_knowledge("nope") is None

    def test_list(self, populated_store):
        entries = populated_store.list_knowledge()
        keys = [e.key for e in entries]
        assert "architecture" in keys
        assert "conventions" in keys
        assert "known-issues" in keys

    def test_rm(self, store):
        store.set_knowledge("temp", "temporary")
        assert store.rm_knowledge("temp")
        assert store.get_knowledge("temp") is None

    def test_rm_nonexistent(self, store):
        assert not store.rm_knowledge("nope")

    def test_key_sanitization(self, store):
        store.set_knowledge("My Cool Topic!", "content")
        entry = store.get_knowledge("my-cool-topic")
        assert entry is not None


class TestDecisions:
    def test_add_and_get(self, store):
        dec = store.add_decision(title="Use Redis", context="Need caching")
        assert dec.id == 1
        assert dec.title == "Use Redis"

        retrieved = store.get_decision("1")
        assert retrieved is not None
        assert retrieved.title == "Use Redis"
        assert "Need caching" in retrieved.context

    def test_auto_numbering(self, store):
        store.add_decision(title="First")
        store.add_decision(title="Second")
        store.add_decision(title="Third")
        decisions = store.list_decisions()
        assert [d.id for d in decisions] == [1, 2, 3]

    def test_get_by_title(self, store):
        store.add_decision(title="Use PostgreSQL over SQLite")
        dec = store.get_decision("postgresql")
        assert dec is not None
        assert "PostgreSQL" in dec.title

    def test_list_empty(self, store):
        assert store.list_decisions() == []


class TestState:
    def test_active_state_roundtrip(self, store):
        state = ActiveState(
            current_task="Implementing auth",
            blockers=["Need API keys"],
            last_agent="claude-code",
        )
        store.write_active_state(state)
        read = store.read_active_state()
        assert read.current_task == "Implementing auth"
        assert read.blockers == ["Need API keys"]

    def test_default_state(self, store):
        state = store.read_active_state()
        assert state.current_task == ""


class TestHistory:
    def test_append_and_list(self, store):
        s1 = SessionSummary(agent="claude-code", summary="Did stuff")
        s2 = SessionSummary(agent="opencode", summary="More stuff")
        store.append_session(s1)
        store.append_session(s2)
        sessions = store.list_sessions()
        assert len(sessions) == 2
        assert sessions[0].agent == "claude-code"
        assert sessions[1].agent == "opencode"


class TestSummary:
    def test_summary(self, populated_store):
        s = populated_store.summary()
        assert s["project"] == "test-project"
        assert s["knowledge_count"] == 3
        assert s["decision_count"] == 2
        assert "architecture" in s["knowledge_keys"]
