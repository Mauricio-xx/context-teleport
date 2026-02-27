"""Tests for conventions in dotpath resolution."""

from __future__ import annotations

import pytest

from ctx.core.dotpath import resolve_dotpath, set_dotpath


class TestDotpathConventions:
    def test_resolve_all_conventions(self, store):
        store.set_convention("git", "Use branches.")
        store.set_convention("env", "No sudo.")
        result = resolve_dotpath(store, "conventions")
        assert isinstance(result, dict)
        assert "git" in result
        assert "env" in result

    def test_resolve_single_convention(self, store):
        store.set_convention("git", "Use branches.")
        result = resolve_dotpath(store, "conventions.git")
        assert result == "Use branches."

    def test_resolve_missing_convention(self, store):
        result = resolve_dotpath(store, "conventions.nonexistent")
        assert result is None

    def test_set_convention_via_dotpath(self, store):
        set_dotpath(store, "conventions.git", "Use branches.")
        entry = store.get_convention("git")
        assert entry is not None
        assert entry.content == "Use branches."

    def test_set_convention_no_key_raises(self, store):
        with pytest.raises(ValueError, match="convention key"):
            set_dotpath(store, "conventions", "value")
