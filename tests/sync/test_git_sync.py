"""Tests for git sync operations."""

from pathlib import Path

import git
import pytest

from ctx.core.conflicts import Strategy
from ctx.core.scope import Scope
from ctx.core.store import ContextStore
from ctx.sync.git_sync import GitSync, GitSyncError
from ctx.utils.paths import STORE_DIR


@pytest.fixture
def two_repos(tmp_path: Path):
    """Create a bare upstream repo and two clones with initialized context stores.

    Returns (upstream_path, clone_a_path, clone_b_path).
    Clone A and B both have the initial context committed and pushed.
    """
    # Create a non-bare seed repo, commit, then clone bare from it.
    # This avoids the "empty bare repo has no branch" issue.
    seed = tmp_path / "seed"
    seed_repo = git.Repo.init(seed)
    (seed / "README.md").write_text("# Test\n")
    seed_repo.index.add(["README.md"])
    seed_repo.index.commit("initial")
    upstream = tmp_path / "upstream.git"
    git.Repo.clone_from(str(seed), str(upstream), bare=True)

    # Clone A: init context store with some baseline knowledge, then push
    clone_a = tmp_path / "clone_a"
    repo_a = git.Repo.clone_from(str(upstream), str(clone_a))

    store_a = ContextStore(clone_a)
    store_a.init(project_name="test-project")
    # Seed knowledge files so both clones have them (avoids empty-dir issues)
    store_a.set_knowledge("arch", "baseline architecture")
    store_a.set_knowledge("stack", "baseline stack")
    repo_a.index.add([STORE_DIR])
    repo_a.index.commit("init context store with baseline knowledge")
    repo_a.remotes.origin.push()

    # Clone B: gets the full context store including knowledge files
    clone_b = tmp_path / "clone_b"
    git.Repo.clone_from(str(upstream), str(clone_b))

    return upstream, clone_a, clone_b


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

    def test_commit_does_not_push(self, two_repos):
        """commit() should only create a local commit, never push."""
        _upstream, clone_a, clone_b = two_repos
        store_a = ContextStore(clone_a)
        store_a.set_knowledge("local-only", "should stay local")

        gs = GitSync(clone_a)
        result = gs.commit()
        assert result["status"] == "committed"
        assert "commit_message" in result

        # Verify the commit exists locally
        repo_a = git.Repo(clone_a)
        assert "local-only" in repo_a.head.commit.message

        # Verify it was NOT pushed (clone_b should not see it after fetch)
        repo_b = git.Repo(clone_b)
        repo_b.remotes.origin.fetch()
        branch = repo_a.active_branch.name
        log_b = repo_b.git.log("--oneline", f"origin/{branch}")
        assert "local-only" not in log_b

    def test_commit_nothing(self, store):
        """commit() with no changes returns nothing_to_commit."""
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        gs = GitSync(store.root)
        result = gs.commit()
        assert result["status"] == "nothing_to_commit"


class TestConflictPersistence:
    def test_save_and_load_report(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        from ctx.core.conflicts import ConflictEntry, ConflictReport
        gs = GitSync(store.root)

        report = ConflictReport(conflicts=[
            ConflictEntry("knowledge/arch.md", "ours", "theirs", "base"),
        ])
        gs.save_pending_report(report)

        loaded = gs.load_pending_report()
        assert loaded is not None
        assert loaded.conflict_id == report.conflict_id
        assert len(loaded.conflicts) == 1
        assert loaded.conflicts[0].file_path == "knowledge/arch.md"
        assert loaded.conflicts[0].ours_content == "ours"

    def test_clear_pending_report(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        from ctx.core.conflicts import ConflictReport
        gs = GitSync(store.root)

        gs.save_pending_report(ConflictReport())
        assert gs.has_pending_conflicts()

        gs.clear_pending_report()
        assert not gs.has_pending_conflicts()
        assert gs.load_pending_report() is None

    def test_has_pending_false_when_no_file(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        gs = GitSync(store.root)
        assert not gs.has_pending_conflicts()

    def test_load_returns_none_for_corrupt_file(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        gs = GitSync(store.root)
        gs._pending_path().write_text("not json at all {{{")
        assert gs.load_pending_report() is None

    def test_pull_agent_strategy_persists_report(self, two_repos):
        _, clone_a, clone_b = two_repos

        store_a = ContextStore(clone_a)
        store_a.set_knowledge("arch", "Version from A")
        repo_a = git.Repo(clone_a)
        repo_a.index.add([STORE_DIR])
        repo_a.index.commit("A: update arch")
        repo_a.remotes.origin.push()

        store_b = ContextStore(clone_b)
        store_b.set_knowledge("arch", "Version from B")
        repo_b = git.Repo(clone_b)
        repo_b.index.add([STORE_DIR])
        repo_b.index.commit("B: update arch")

        gs_b = GitSync(clone_b)
        result = gs_b.pull(strategy=Strategy.agent)
        assert result["status"] == "conflicts"

        # Report persisted to disk
        assert gs_b.has_pending_conflicts()
        loaded = gs_b.load_pending_report()
        assert loaded is not None
        assert loaded.unresolved_count > 0

    def test_apply_resolutions_clears_pending(self, two_repos):
        _, clone_a, clone_b = two_repos

        store_a = ContextStore(clone_a)
        store_a.set_knowledge("arch", "Version from A")
        repo_a = git.Repo(clone_a)
        repo_a.index.add([STORE_DIR])
        repo_a.index.commit("A: update arch")
        repo_a.remotes.origin.push()

        store_b = ContextStore(clone_b)
        store_b.set_knowledge("arch", "Version from B")
        repo_b = git.Repo(clone_b)
        repo_b.index.add([STORE_DIR])
        repo_b.index.commit("B: update arch")

        gs_b = GitSync(clone_b)
        result = gs_b.pull(strategy=Strategy.agent)
        assert result["status"] == "conflicts"
        assert gs_b.has_pending_conflicts()

        report = gs_b.load_pending_report()
        resolutions = [(c.file_path, c.theirs_content) for c in report.conflicts]
        gs_b.apply_resolutions(resolutions)

        assert not gs_b.has_pending_conflicts()


class TestApplyResolutions:
    def test_apply_resolutions_success(self, two_repos):
        """Create a conflict between two clones, resolve interactively."""
        _, clone_a, clone_b = two_repos

        # Clone A: modify a knowledge file and push
        store_a = ContextStore(clone_a)
        store_a.set_knowledge("arch", "Version from A")
        repo_a = git.Repo(clone_a)
        repo_a.index.add([STORE_DIR])
        repo_a.index.commit("A: update arch")
        repo_a.remotes.origin.push()

        # Clone B: modify the same file differently (diverge)
        store_b = ContextStore(clone_b)
        store_b.set_knowledge("arch", "Version from B")
        repo_b = git.Repo(clone_b)
        repo_b.index.add([STORE_DIR])
        repo_b.index.commit("B: update arch")

        # Pull with interactive strategy -- should detect conflict and abort merge
        gs_b = GitSync(clone_b)
        result = gs_b.pull(strategy=Strategy.interactive)
        assert result["status"] == "conflicts"
        assert gs_b._pending_report is not None

        # Build resolutions (choose "theirs" = clone A's version)
        conflict = gs_b._pending_report.conflicts[0]
        resolutions = [(conflict.file_path, conflict.theirs_content)]

        # Apply
        apply_result = gs_b.apply_resolutions(resolutions)
        assert apply_result["status"] == "merged"
        assert apply_result["strategy"] == "interactive"
        assert apply_result["resolved"] == 1
        assert apply_result["skipped"] == 0

        # Verify the file has the resolved content
        resolved_content = (clone_b / conflict.file_path).read_text()
        assert "Version from A" in resolved_content

    def test_apply_with_skipped_files(self, two_repos):
        """Skipped files should get 'ours' content."""
        _, clone_a, clone_b = two_repos

        # Clone A: modify two knowledge files and push
        store_a = ContextStore(clone_a)
        store_a.set_knowledge("arch", "A-arch")
        store_a.set_knowledge("stack", "A-stack")
        repo_a = git.Repo(clone_a)
        repo_a.index.add([STORE_DIR])
        repo_a.index.commit("A: update arch and stack")
        repo_a.remotes.origin.push()

        # Clone B: modify the same files differently
        store_b = ContextStore(clone_b)
        store_b.set_knowledge("arch", "B-arch")
        store_b.set_knowledge("stack", "B-stack")
        repo_b = git.Repo(clone_b)
        repo_b.index.add([STORE_DIR])
        repo_b.index.commit("B: update arch and stack")

        gs_b = GitSync(clone_b)
        result = gs_b.pull(strategy=Strategy.interactive)
        assert result["status"] == "conflicts"

        # Resolve only one file, skip the other
        conflicts = gs_b._pending_report.conflicts
        assert len(conflicts) == 2
        # Sort for determinism
        conflicts.sort(key=lambda c: c.file_path)

        # Resolve first, skip second
        resolutions = [(conflicts[0].file_path, conflicts[0].theirs_content)]

        apply_result = gs_b.apply_resolutions(resolutions)
        assert apply_result["status"] == "merged"
        assert apply_result["resolved"] == 1
        assert apply_result["skipped"] == 1

    def test_apply_no_conflicts(self, two_repos):
        """If re-merge succeeds (e.g., remote conflict resolved), return 'pulled'."""
        _, clone_a, clone_b = two_repos

        # Clone A: modify a file and push
        store_a = ContextStore(clone_a)
        store_a.set_knowledge("arch", "A-only change")
        repo_a = git.Repo(clone_a)
        repo_a.index.add([STORE_DIR])
        repo_a.index.commit("A: update arch")
        repo_a.remotes.origin.push()

        # Clone B: no conflicting changes, just needs to pull
        gs_b = GitSync(clone_b)
        # apply_resolutions should pull cleanly
        result = gs_b.apply_resolutions([])
        assert result["status"] == "pulled"


class TestScopeSync:
    def test_push_excludes_private_knowledge(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        store.set_knowledge("public-arch", "Public architecture")
        store.set_knowledge("private-notes", "Secret notes", scope=Scope.private)

        gs = GitSync(store.root)
        result = gs.push()
        assert result["status"] == "committed"

        # Verify: the private file should not be in the committed tree
        tree = repo.head.commit.tree
        store_tree = tree[STORE_DIR]
        knowledge_tree = store_tree["knowledge"]
        committed_names = [blob.name for blob in knowledge_tree.blobs]
        assert "public-arch.md" in committed_names
        assert "private-notes.md" not in committed_names

    def test_push_excludes_ephemeral(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        store.set_knowledge("scratch", "Ephemeral scratch", scope=Scope.ephemeral)

        gs = GitSync(store.root)
        result = gs.push()
        assert result["status"] == "committed"

        tree = repo.head.commit.tree
        knowledge_tree = tree[STORE_DIR]["knowledge"]
        committed_names = [blob.name for blob in knowledge_tree.blobs]
        assert "scratch.md" not in committed_names

    def test_push_includes_scope_json(self, store):
        repo = git.Repo(store.root)
        repo.index.add([".context-teleport"])
        repo.index.commit("init store")

        store.set_knowledge("private-stuff", "Secret", scope=Scope.private)

        gs = GitSync(store.root)
        gs.push()

        tree = repo.head.commit.tree
        knowledge_tree = tree[STORE_DIR]["knowledge"]
        committed_names = [blob.name for blob in knowledge_tree.blobs]
        assert ".scope.json" in committed_names


class TestSectionMerge:
    def test_different_sections_auto_merged(self, two_repos):
        """Both add different sections at EOF -> git conflicts -> section merge resolves."""
        _, clone_a, clone_b = two_repos

        # Both start with same single-section file
        base_content = "## Core\nShared core logic\n"
        store_a = ContextStore(clone_a)
        store_a.set_knowledge("arch", base_content)
        repo_a = git.Repo(clone_a)
        repo_a.index.add([STORE_DIR])
        repo_a.index.commit("setup single-section arch")
        repo_a.remotes.origin.push()

        # Clone B: pull to get baseline
        repo_b = git.Repo(clone_b)
        repo_b.remotes.origin.pull()

        # Clone A: add Frontend section at end
        store_a.set_knowledge(
            "arch",
            "## Core\nShared core logic\n\n## Frontend\nReact with TypeScript\n",
        )
        repo_a.index.add([STORE_DIR])
        repo_a.index.commit("A: add frontend section")
        repo_a.remotes.origin.push()

        # Clone B: add DevOps section at end (different section, same position)
        store_b = ContextStore(clone_b)
        store_b.set_knowledge(
            "arch",
            "## Core\nShared core logic\n\n## DevOps\nDocker and Kubernetes\n",
        )
        repo_b.index.add([STORE_DIR])
        repo_b.index.commit("B: add devops section")

        # Pull should trigger git conflict (both added at EOF), section merge resolves
        gs_b = GitSync(clone_b)
        result = gs_b.pull()
        assert result["status"] == "merged"
        assert result.get("strategy") == "section-auto"

        # Verify merged content has both new sections plus original
        merged = store_b.get_knowledge("arch")
        assert "Shared core logic" in merged.content
        assert "React" in merged.content
        assert "Docker" in merged.content

    def test_same_section_conflict(self, two_repos):
        """Both modify same line/section -> section merge can't resolve -> ours strategy."""
        _, clone_a, clone_b = two_repos

        base_content = "## Backend\nPython with FastAPI\n\n## Frontend\nReact\n"
        store_a = ContextStore(clone_a)
        store_a.set_knowledge("arch", base_content)
        repo_a = git.Repo(clone_a)
        repo_a.index.add([STORE_DIR])
        repo_a.index.commit("setup multi-section arch")
        repo_a.remotes.origin.push()

        repo_b = git.Repo(clone_b)
        repo_b.remotes.origin.pull()

        # Clone A: modify Backend section (changes line 2)
        store_a.set_knowledge(
            "arch",
            "## Backend\nPython with Django\n\n## Frontend\nReact\n",
        )
        repo_a.index.add([STORE_DIR])
        repo_a.index.commit("A: Django")
        repo_a.remotes.origin.push()

        # Clone B: also modify Backend section (same line, different value)
        store_b = ContextStore(clone_b)
        store_b.set_knowledge(
            "arch",
            "## Backend\nRuby on Rails\n\n## Frontend\nReact\n",
        )
        repo_b.index.add([STORE_DIR])
        repo_b.index.commit("B: Rails")

        gs_b = GitSync(clone_b)
        result = gs_b.pull()
        # Section merge finds conflict in Backend, falls through to ours strategy
        assert result["status"] == "merged"
        assert result.get("strategy") == "ours"

    def test_add_and_edit_auto_merged(self, two_repos):
        """One adds section + other edits existing and adds different section -> auto-merged."""
        _, clone_a, clone_b = two_repos

        base_content = "## Backend\nPython\n"
        store_a = ContextStore(clone_a)
        store_a.set_knowledge("arch", base_content)
        repo_a = git.Repo(clone_a)
        repo_a.index.add([STORE_DIR])
        repo_a.index.commit("setup single-section arch")
        repo_a.remotes.origin.push()

        repo_b = git.Repo(clone_b)
        repo_b.remotes.origin.pull()

        # Clone A: add Frontend section at end
        store_a.set_knowledge(
            "arch",
            "## Backend\nPython\n\n## Frontend\nReact\n",
        )
        repo_a.index.add([STORE_DIR])
        repo_a.index.commit("A: add frontend")
        repo_a.remotes.origin.push()

        # Clone B: modify Backend + add Infra at end (overlaps with A's addition)
        store_b = ContextStore(clone_b)
        store_b.set_knowledge(
            "arch",
            "## Backend\nPython with FastAPI\n\n## Infra\nDocker\n",
        )
        repo_b.index.add([STORE_DIR])
        repo_b.index.commit("B: edit backend + add infra")

        gs_b = GitSync(clone_b)
        result = gs_b.pull()
        assert result["status"] == "merged"

        # Verify all sections present
        merged = store_b.get_knowledge("arch")
        assert "FastAPI" in merged.content
        assert "React" in merged.content or "Frontend" in merged.content
        assert "Docker" in merged.content
