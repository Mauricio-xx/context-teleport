"""Tests for full-text search."""

from ctx.core.search import search_files


class TestSearch:
    def test_basic_search(self, populated_store):
        results = search_files(populated_store.knowledge_dir(), "hexagonal")
        assert len(results) > 0
        assert results[0].key == "architecture"

    def test_multi_term(self, populated_store):
        results = search_files(populated_store.knowledge_dir(), "Python pytest")
        assert len(results) > 0
        assert results[0].key == "conventions"

    def test_no_results(self, populated_store):
        results = search_files(populated_store.knowledge_dir(), "quantum-computing")
        assert len(results) == 0

    def test_search_across_decisions(self, populated_store):
        results = search_files(populated_store.store_dir, "PostgreSQL")
        assert len(results) > 0

    def test_result_scoring(self, populated_store):
        # Exact phrase should score higher
        results = search_files(populated_store.knowledge_dir(), "Flaky test")
        assert len(results) > 0
        assert results[0].key == "known-issues"

    def test_exclude_files(self, populated_store):
        results = search_files(
            populated_store.knowledge_dir(),
            "hexagonal",
            exclude_files={"architecture.md"},
        )
        # architecture.md contains "hexagonal" but should be excluded
        assert all(r.key != "architecture" for r in results)
