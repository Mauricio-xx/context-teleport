"""Shared fixtures: temp git repos, mock stores."""

from __future__ import annotations

from pathlib import Path

import git
import pytest

from ctx.core.store import ContextStore


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository."""
    repo = git.Repo.init(tmp_path)
    # Need at least one commit for HEAD to be valid
    readme = tmp_path / "README.md"
    readme.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    return tmp_path


@pytest.fixture
def store(tmp_git_repo: Path) -> ContextStore:
    """Create an initialized ContextStore in a temp git repo."""
    s = ContextStore(tmp_git_repo)
    s.init(project_name="test-project")
    return s


@pytest.fixture
def populated_store(store: ContextStore) -> ContextStore:
    """Store with some knowledge and decisions pre-populated."""
    store.set_knowledge("architecture", "Hexagonal architecture with ports and adapters")
    store.set_knowledge("conventions", "Python 3.11+, ruff linter, pytest for tests")
    store.set_knowledge("known-issues", "Flaky test in auth module")
    store.add_decision(
        title="Use PostgreSQL",
        context="Need a production database",
        decision_text="PostgreSQL over SQLite",
        consequences="Requires managed DB",
    )
    store.add_decision(
        title="Use Redis for caching",
        context="Need caching layer",
        decision_text="Redis for session + query cache",
        consequences="Additional infrastructure",
    )
    return store
