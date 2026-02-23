"""Tests for ContextStore."""

import pytest

from ctx.core.schema import ActiveState, SessionSummary
from ctx.core.scope import Scope
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


class TestScoping:
    def test_default_scope_is_public(self, store):
        store.set_knowledge("arch", "Architecture notes")
        assert store.get_knowledge_scope("arch") == Scope.public

    def test_set_knowledge_with_scope(self, store):
        store.set_knowledge("notes", "Private notes", scope=Scope.private)
        assert store.get_knowledge_scope("notes") == Scope.private

    def test_list_knowledge_filter_by_scope(self, store):
        store.set_knowledge("public-info", "Public stuff")
        store.set_knowledge("private-info", "Private stuff", scope=Scope.private)
        store.set_knowledge("ephemeral-info", "Ephemeral stuff", scope=Scope.ephemeral)

        all_entries = store.list_knowledge()
        assert len(all_entries) == 3

        public = store.list_knowledge(scope=Scope.public)
        assert [e.key for e in public] == ["public-info"]

        private = store.list_knowledge(scope=Scope.private)
        assert [e.key for e in private] == ["private-info"]

    def test_set_knowledge_scope_existing(self, store):
        store.set_knowledge("arch", "Architecture notes")
        assert store.set_knowledge_scope("arch", Scope.private)
        assert store.get_knowledge_scope("arch") == Scope.private

    def test_set_knowledge_scope_nonexistent(self, store):
        assert not store.set_knowledge_scope("ghost", Scope.private)

    def test_rm_cleans_sidecar(self, store):
        store.set_knowledge("temp", "Temp content", scope=Scope.private)
        assert store.get_knowledge_scope("temp") == Scope.private
        store.rm_knowledge("temp")
        # Sidecar entry should be gone
        assert store.get_knowledge_scope("temp") == Scope.public

    def test_gitignore_updated_on_scope_change(self, store):
        store.set_knowledge("secret", "Sensitive", scope=Scope.private)
        gitignore = (store.store_dir / ".gitignore").read_text()
        assert "knowledge/secret.md" in gitignore

        store.set_knowledge_scope("secret", Scope.public)
        gitignore = (store.store_dir / ".gitignore").read_text()
        assert "knowledge/secret.md" not in gitignore

    def test_add_decision_with_scope(self, store):
        dec = store.add_decision(title="Private Decision", scope=Scope.private)
        assert store.get_decision_scope(str(dec.id)) == Scope.private

    def test_list_decisions_filter_by_scope(self, store):
        store.add_decision(title="Public Dec")
        store.add_decision(title="Private Dec", scope=Scope.private)

        all_decs = store.list_decisions()
        assert len(all_decs) == 2

        public = store.list_decisions(scope=Scope.public)
        assert len(public) == 1
        assert public[0].title == "Public Dec"

    def test_init_creates_scope_files(self, tmp_git_repo):
        s = ContextStore(tmp_git_repo)
        s.init(project_name="scoped-project")
        assert (s.store_dir / "knowledge" / ".scope.json").is_file()
        assert (s.store_dir / "knowledge" / "decisions" / ".scope.json").is_file()


class TestSummary:
    def test_summary(self, populated_store):
        s = populated_store.summary()
        assert s["project"] == "test-project"
        assert s["knowledge_count"] == 3
        assert s["decision_count"] == 2
        assert "architecture" in s["knowledge_keys"]
