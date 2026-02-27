"""Tests for convention CRUD, scope, author tracking, gitignore, ephemeral, summary."""


from ctx.core.scope import Scope
from ctx.core.store import ContextStore


class TestConventionCRUD:
    def test_set_and_get(self, store):
        entry = store.set_convention("git", "Always use feature branches.")
        assert entry.key == "git"
        assert entry.content == "Always use feature branches."

        fetched = store.get_convention("git")
        assert fetched is not None
        assert fetched.key == "git"
        assert fetched.content == "Always use feature branches."

    def test_get_missing_returns_none(self, store):
        assert store.get_convention("nonexistent") is None

    def test_list_empty(self, store):
        assert store.list_conventions() == []

    def test_list_returns_all(self, store):
        store.set_convention("git", "Use branches.")
        store.set_convention("env", "No sudo.")
        entries = store.list_conventions()
        assert len(entries) == 2
        keys = [e.key for e in entries]
        assert "env" in keys
        assert "git" in keys

    def test_overwrite_existing(self, store):
        store.set_convention("git", "v1")
        store.set_convention("git", "v2")
        entry = store.get_convention("git")
        assert entry.content == "v2"

    def test_rm_existing(self, store):
        store.set_convention("git", "content")
        assert store.rm_convention("git") is True
        assert store.get_convention("git") is None

    def test_rm_missing(self, store):
        assert store.rm_convention("nonexistent") is False

    def test_key_sanitization(self, store):
        store.set_convention("Git Conventions!", "content")
        entry = store.get_convention("git-conventions")
        assert entry is not None


class TestConventionAuthor:
    def test_author_set_on_write(self, store):
        store.set_convention("git", "content", author="alice")
        entry = store.get_convention("git")
        assert entry.author == "alice"

    def test_author_default(self, store):
        store.set_convention("git", "content")
        entry = store.get_convention("git")
        # Default author comes from get_author()
        assert entry.author != ""

    def test_author_cleaned_on_rm(self, store):
        store.set_convention("git", "content", author="alice")
        store.rm_convention("git")
        meta = store._read_convention_meta()
        assert "git.md" not in meta


class TestConventionScope:
    def test_default_scope_public(self, store):
        store.set_convention("git", "content")
        assert store.get_convention_scope("git") == Scope.public

    def test_set_scope(self, store):
        store.set_convention("git", "content")
        assert store.set_convention_scope("git", Scope.private) is True
        assert store.get_convention_scope("git") == Scope.private

    def test_set_scope_missing(self, store):
        assert store.set_convention_scope("nonexistent", Scope.private) is False

    def test_scope_on_create(self, store):
        store.set_convention("git", "content", scope=Scope.ephemeral)
        assert store.get_convention_scope("git") == Scope.ephemeral

    def test_list_with_scope_filter(self, store):
        store.set_convention("git", "public", scope=Scope.public)
        store.set_convention("env", "private", scope=Scope.private)
        pub = store.list_conventions(scope=Scope.public)
        assert len(pub) == 1
        assert pub[0].key == "git"


class TestConventionGitignore:
    def test_private_convention_in_gitignore(self, store):
        store.set_convention("secret", "hidden", scope=Scope.private)
        gitignore = (store.store_dir / ".gitignore").read_text()
        assert "conventions/secret.md" in gitignore

    def test_public_convention_not_in_gitignore(self, store):
        store.set_convention("git", "public")
        gitignore = (store.store_dir / ".gitignore").read_text()
        assert "conventions/git.md" not in gitignore

    def test_gitignore_updated_on_scope_change(self, store):
        store.set_convention("git", "content", scope=Scope.public)
        store.set_convention_scope("git", Scope.private)
        gitignore = (store.store_dir / ".gitignore").read_text()
        assert "conventions/git.md" in gitignore


class TestConventionEphemeral:
    def test_clear_ephemeral_removes_conventions(self, store):
        store.set_convention("keep", "public")
        store.set_convention("remove", "temp", scope=Scope.ephemeral)

        removed = store.clear_ephemeral()
        assert removed["conventions"] == 1
        assert store.get_convention("keep") is not None
        assert store.get_convention("remove") is None

    def test_clear_ephemeral_cleans_meta(self, store):
        store.set_convention("temp", "content", author="bot", scope=Scope.ephemeral)
        store.clear_ephemeral()
        meta = store._read_convention_meta()
        assert "temp.md" not in meta


class TestConventionInSummary:
    def test_summary_includes_conventions(self, store):
        store.set_convention("git", "use branches")
        store.set_convention("env", "no sudo")
        s = store.summary()
        assert s["convention_count"] == 2
        assert "git" in s["convention_keys"]
        assert "env" in s["convention_keys"]

    def test_summary_empty_conventions(self, store):
        s = store.summary()
        assert s["convention_count"] == 0
        assert s["convention_keys"] == []


class TestConventionInit:
    def test_init_creates_conventions_dir(self, tmp_git_repo):
        store = ContextStore(tmp_git_repo)
        store.init(project_name="test")
        assert (store.store_dir / "conventions").is_dir()
        assert (store.store_dir / "conventions" / ".scope.json").is_file()

    def test_lazy_dir_creation_for_preexisting_store(self, store):
        """set_convention creates conventions/ dir lazily if it doesn't exist."""
        import shutil
        cdir = store.conventions_dir()
        if cdir.is_dir():
            shutil.rmtree(cdir)
        store.set_convention("git", "use branches")
        assert store.get_convention("git") is not None
