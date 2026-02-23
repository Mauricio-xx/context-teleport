"""Tests for scope sidecar management."""

import json

import pytest

from ctx.core.scope import Scope, ScopeMap


@pytest.fixture
def scope_dir(tmp_path):
    """A temporary directory for scope tests."""
    return tmp_path / "knowledge"


@pytest.fixture
def scope_map(scope_dir):
    scope_dir.mkdir()
    return ScopeMap(scope_dir)


class TestScopeEnum:
    def test_values(self):
        assert Scope.public.value == "public"
        assert Scope.private.value == "private"
        assert Scope.ephemeral.value == "ephemeral"

    def test_from_string(self):
        assert Scope("private") == Scope.private


class TestScopeMap:
    def test_default_is_public(self, scope_map):
        assert scope_map.get("arch.md") == Scope.public

    def test_set_and_get(self, scope_map):
        scope_map.set("notes.md", Scope.private)
        assert scope_map.get("notes.md") == Scope.private

    def test_set_public_removes_entry(self, scope_map):
        scope_map.set("notes.md", Scope.private)
        scope_map.set("notes.md", Scope.public)
        data = json.loads((scope_map.directory / ".scope.json").read_text())
        assert "notes.md" not in data

    def test_set_ephemeral(self, scope_map):
        scope_map.set("scratch.md", Scope.ephemeral)
        assert scope_map.get("scratch.md") == Scope.ephemeral

    def test_remove_cleans_sidecar(self, scope_map):
        scope_map.set("temp.md", Scope.private)
        scope_map.remove("temp.md")
        assert scope_map.get("temp.md") == Scope.public

    def test_remove_nonexistent_is_noop(self, scope_map):
        scope_map.remove("ghost.md")  # should not raise

    def test_non_public_files(self, scope_map):
        scope_map.set("a.md", Scope.private)
        scope_map.set("b.md", Scope.ephemeral)
        scope_map.set("c.md", Scope.public)
        result = scope_map.non_public_files()
        assert result == {"a.md", "b.md"}

    def test_list_by_scope_private(self, scope_map):
        scope_map.set("a.md", Scope.private)
        scope_map.set("b.md", Scope.ephemeral)
        scope_map.set("c.md", Scope.private)
        assert sorted(scope_map.list_by_scope(Scope.private)) == ["a.md", "c.md"]

    def test_list_by_scope_public_returns_empty(self, scope_map):
        # Public files are not tracked in the sidecar
        assert scope_map.list_by_scope(Scope.public) == []

    def test_missing_sidecar_returns_public(self, tmp_path):
        smap = ScopeMap(tmp_path)
        assert smap.get("anything.md") == Scope.public

    def test_corrupt_sidecar_returns_public(self, scope_map):
        (scope_map.directory / ".scope.json").write_text("not json!!")
        assert scope_map.get("anything.md") == Scope.public

    def test_ensure_exists_creates_file(self, tmp_path):
        d = tmp_path / "new_dir"
        d.mkdir()
        ScopeMap.ensure_exists(d)
        path = d / ".scope.json"
        assert path.is_file()
        assert json.loads(path.read_text()) == {}

    def test_ensure_exists_idempotent(self, scope_map):
        scope_map.set("a.md", Scope.private)
        ScopeMap.ensure_exists(scope_map.directory)
        # Should not overwrite existing data
        assert scope_map.get("a.md") == Scope.private
