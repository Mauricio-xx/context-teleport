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


class TestClearEphemeral:
    def test_removes_ephemeral_knowledge(self, store):
        store.set_knowledge("keep-pub", "Public", scope=Scope.public)
        store.set_knowledge("keep-priv", "Private", scope=Scope.private)
        store.set_knowledge("remove-eph", "Ephemeral", scope=Scope.ephemeral)

        removed = store.clear_ephemeral()
        assert removed["knowledge"] == 1
        assert store.get_knowledge("keep-pub") is not None
        assert store.get_knowledge("keep-priv") is not None
        assert store.get_knowledge("remove-eph") is None

    def test_removes_ephemeral_decisions(self, store):
        store.add_decision(title="Keep Public")
        store.add_decision(title="Remove Eph", scope=Scope.ephemeral)

        removed = store.clear_ephemeral()
        assert removed["decisions"] == 1
        decs = store.list_decisions()
        assert len(decs) == 1
        assert decs[0].title == "Keep Public"

    def test_removes_ephemeral_skills(self, store):
        content = "---\nname: keep\ndescription: Keep\n---\n\nBody.\n"
        eph_content = "---\nname: remove\ndescription: Remove\n---\n\nBody.\n"
        store.set_skill("keep", content, scope=Scope.public)
        store.set_skill("remove", eph_content, scope=Scope.ephemeral)

        removed = store.clear_ephemeral()
        assert removed["skills"] == 1
        assert store.get_skill("keep") is not None
        assert store.get_skill("remove") is None
        # Skill directory should be gone
        assert not (store.skills_dir() / "remove").exists()

    def test_preserves_non_ephemeral(self, store):
        store.set_knowledge("pub", "Public")
        store.set_knowledge("priv", "Private", scope=Scope.private)

        removed = store.clear_ephemeral()
        assert removed == {"knowledge": 0, "decisions": 0, "conventions": 0, "skills": 0}
        assert store.get_knowledge("pub") is not None
        assert store.get_knowledge("priv") is not None

    def test_empty_store(self, store):
        removed = store.clear_ephemeral()
        assert removed == {"knowledge": 0, "decisions": 0, "conventions": 0, "skills": 0}


class TestSkills:
    def _sample_skill(self, name="deploy", desc="Deploy to staging"):
        return f"---\nname: {name}\ndescription: {desc}\n---\n\nRun the deploy script.\n"

    def test_set_and_get(self, store):
        content = self._sample_skill()
        store.set_skill("deploy", content)
        entry = store.get_skill("deploy")
        assert entry is not None
        assert entry.name == "deploy"
        assert entry.description == "Deploy to staging"
        assert "deploy script" in entry.content

    def test_get_nonexistent(self, store):
        assert store.get_skill("nope") is None

    def test_list(self, store):
        store.set_skill("deploy", self._sample_skill("deploy", "Deploy"))
        store.set_skill("lint", self._sample_skill("lint", "Run linter"))
        entries = store.list_skills()
        names = [e.name for e in entries]
        assert "deploy" in names
        assert "lint" in names

    def test_rm(self, store):
        store.set_skill("temp", self._sample_skill("temp", "Temporary"))
        assert store.rm_skill("temp")
        assert store.get_skill("temp") is None

    def test_rm_nonexistent(self, store):
        assert not store.rm_skill("nope")

    def test_scope_default_public(self, store):
        store.set_skill("deploy", self._sample_skill())
        assert store.get_skill_scope("deploy") == Scope.public

    def test_scope_set_and_get(self, store):
        store.set_skill("deploy", self._sample_skill(), scope=Scope.private)
        assert store.get_skill_scope("deploy") == Scope.private

    def test_scope_change(self, store):
        store.set_skill("deploy", self._sample_skill())
        assert store.set_skill_scope("deploy", Scope.private)
        assert store.get_skill_scope("deploy") == Scope.private

    def test_scope_change_nonexistent(self, store):
        assert not store.set_skill_scope("ghost", Scope.private)

    def test_list_filter_by_scope(self, store):
        store.set_skill("pub", self._sample_skill("pub", "Public"))
        store.set_skill("priv", self._sample_skill("priv", "Private"), scope=Scope.private)
        public = store.list_skills(scope=Scope.public)
        assert [e.name for e in public] == ["pub"]
        private = store.list_skills(scope=Scope.private)
        assert [e.name for e in private] == ["priv"]

    def test_rm_cleans_scope(self, store):
        store.set_skill("temp", self._sample_skill("temp", "Temp"), scope=Scope.private)
        assert store.get_skill_scope("temp") == Scope.private
        store.rm_skill("temp")
        assert store.get_skill_scope("temp") == Scope.public

    def test_init_creates_skills_dir(self, tmp_git_repo):
        s = ContextStore(tmp_git_repo)
        s.init(project_name="skills-project")
        assert (s.store_dir / "skills").is_dir()
        assert (s.store_dir / "skills" / ".scope.json").is_file()

    def test_name_from_frontmatter(self, store):
        """Name comes from frontmatter, not directory name."""
        content = "---\nname: My Fancy Skill\ndescription: Does things\n---\n\nBody.\n"
        store.set_skill("my-fancy-skill", content)
        entry = store.get_skill("my-fancy-skill")
        assert entry.name == "My Fancy Skill"

    def test_no_frontmatter_uses_dir_name(self, store):
        store.set_skill("plain", "Just plain instructions, no frontmatter.")
        entry = store.get_skill("plain")
        assert entry.name == "plain"
        assert entry.description == ""


class TestSummary:
    def test_summary(self, populated_store):
        s = populated_store.summary()
        assert s["project"] == "test-project"
        assert s["knowledge_count"] == 3
        assert s["decision_count"] == 2
        assert "architecture" in s["knowledge_keys"]
        assert s["skill_count"] == 0
        assert s["skill_names"] == []

    def test_summary_with_skills(self, store):
        store.set_skill("deploy", "---\nname: deploy\ndescription: Deploy\n---\n\nBody.\n")
        s = store.summary()
        assert s["skill_count"] == 1
        assert "deploy" in s["skill_names"]


class TestSkillNameSanitization:
    """Verify skill names are sanitized to prevent path traversal."""

    _SKILL_CONTENT = "---\nname: test\ndescription: Test\n---\n\nBody.\n"

    def test_path_traversal_sanitized_set(self, store):
        """Path traversal chars get stripped by sanitize_key; file lands inside skills/."""
        store.set_skill("../../etc/passwd", self._SKILL_CONTENT)
        # The dots and slashes get replaced, skill is stored as "etc-passwd"
        assert store.get_skill("etc-passwd") is not None
        # No file outside the skills dir
        assert not (store.root / "etc").exists()

    def test_path_traversal_sanitized_get(self, store):
        store.set_skill("../../etc/passwd", self._SKILL_CONTENT)
        entry = store.get_skill("../../etc/passwd")
        assert entry is not None
        assert entry.name == "test"

    def test_path_traversal_sanitized_rm(self, store):
        store.set_skill("../../../tmp/evil", self._SKILL_CONTENT)
        assert store.rm_skill("../../../tmp/evil")
        assert not (store.root / "tmp").exists()

    def test_path_traversal_sanitized_usage(self, store):
        store.set_skill("../../etc/passwd", self._SKILL_CONTENT)
        # Should record usage for the sanitized name, not traverse
        event = store.record_skill_usage("../../etc/passwd")
        assert event is not None

    def test_path_traversal_sanitized_feedback(self, store):
        store.set_skill("../../etc/passwd", self._SKILL_CONTENT)
        fb = store.add_skill_feedback("../../etc/passwd", 5)
        assert fb is not None

    def test_empty_name_rejected(self, store):
        """Empty or whitespace-only names are rejected."""
        with pytest.raises((StoreError, ValueError)):
            store.set_skill("   ", self._SKILL_CONTENT)

    def test_name_normalization(self, store):
        """Special chars get sanitized, not rejected."""
        store.set_skill("My Skill!", self._SKILL_CONTENT)
        entry = store.get_skill("my-skill")
        assert entry is not None

    def test_normalized_name_roundtrip(self, store):
        """Setting with unclean name, getting with clean name works."""
        store.set_skill("Deploy Script!", self._SKILL_CONTENT)
        assert store.get_skill("deploy-script") is not None
        assert store.rm_skill("deploy-script")

    def test_skill_stored_in_skills_dir_only(self, store):
        """Regardless of input name, files only appear under skills_dir."""
        store.set_skill("../../outside", self._SKILL_CONTENT)
        # Verify the skill directory is inside skills_dir
        skills_dir = store.skills_dir()
        skill_dirs = [d.name for d in skills_dir.iterdir() if d.is_dir()]
        assert "outside" in skill_dirs  # sanitized to "outside"
        # Nothing escaped
        assert not (store.root / "outside").exists()
