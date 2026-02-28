"""Tests for markdown navigation MCP tools."""

import json

from ctx.mcp.server import (
    context_get_section,
    context_list_tables,
    context_outline,
    set_store,
)


class TestContextOutline:
    def test_outline_with_headings(self, store):
        set_store(store)
        store.set_knowledge("arch", "# Architecture\n\n## Backend\nDjango\n\n## Frontend\nReact\n\n### Components\nButtons\n")
        result = json.loads(context_outline("arch"))
        assert len(result) == 4
        assert result[0]["heading"] == "Architecture"
        assert result[0]["level"] == 1
        assert result[1]["heading"] == "Backend"
        assert result[1]["level"] == 2
        assert result[3]["heading"] == "Components"
        assert result[3]["level"] == 3

    def test_outline_no_headings(self, store):
        set_store(store)
        store.set_knowledge("plain", "Just plain text without any headings.")
        result = json.loads(context_outline("plain"))
        assert result == []

    def test_outline_entry_not_found(self, store):
        set_store(store)
        result = json.loads(context_outline("nonexistent"))
        assert "error" in result

    def test_outline_convention(self, store):
        set_store(store)
        store.set_convention("git", "## Branching\nUse feature branches\n\n## Commits\nConventional commits\n")
        result = json.loads(context_outline("git"))
        assert len(result) == 2
        assert result[0]["heading"] == "Branching"

    def test_outline_skill(self, store):
        set_store(store)
        store.set_skill("deploy", "---\nname: deploy\ndescription: Deploy\n---\n\n## Steps\n1. Build\n2. Deploy\n\n## Rollback\nRevert\n")
        result = json.loads(context_outline("deploy"))
        headings = [h["heading"] for h in result]
        assert "Steps" in headings
        assert "Rollback" in headings


class TestContextGetSection:
    def test_get_existing_section(self, store):
        set_store(store)
        store.set_knowledge("arch", "## Backend\nDjango with DRF\n\n## Frontend\nReact with TypeScript\n")
        result = json.loads(context_get_section("arch", "Backend"))
        assert "Django" in result["content"]
        assert "## Backend" in result["heading"]

    def test_get_section_case_insensitive(self, store):
        set_store(store)
        store.set_knowledge("arch", "## Backend\nDjango\n\n## Frontend\nReact\n")
        result = json.loads(context_get_section("arch", "backend"))
        assert "Django" in result["content"]

    def test_get_section_partial_match(self, store):
        set_store(store)
        store.set_knowledge("arch", "## Backend Architecture\nMicroservices\n\n## Frontend\nReact\n")
        result = json.loads(context_get_section("arch", "backend"))
        assert "Microservices" in result["content"]

    def test_get_section_not_found(self, store):
        set_store(store)
        store.set_knowledge("arch", "## Backend\nDjango\n")
        result = json.loads(context_get_section("arch", "database"))
        assert "error" in result

    def test_get_section_entry_not_found(self, store):
        set_store(store)
        result = json.loads(context_get_section("nonexistent", "backend"))
        assert "error" in result

    def test_get_section_deeper_headings(self, store):
        set_store(store)
        store.set_knowledge("arch", "# Arch\n\n## Backend\nDjango\n\n### Models\nUser model\n\n## Frontend\nReact\n")
        result = json.loads(context_get_section("arch", "Models"))
        assert "User model" in result["content"]


class TestContextListTables:
    def test_list_tables(self, store):
        set_store(store)
        store.set_knowledge("comparison", (
            "## Databases\n\n"
            "| Name | Type |\n"
            "|------|------|\n"
            "| PostgreSQL | Relational |\n"
            "| MongoDB | Document |\n"
            "\n## Summary\nDone.\n"
        ))
        result = json.loads(context_list_tables("comparison"))
        assert len(result) == 1
        assert result[0]["heading"] == "Databases"
        assert result[0]["rows"] == 3  # header + 2 data rows
        assert "PostgreSQL" in result[0]["content"]

    def test_list_tables_multiple(self, store):
        set_store(store)
        store.set_knowledge("multi", (
            "## Section A\n\n"
            "| A | B |\n"
            "|---|---|\n"
            "| 1 | 2 |\n"
            "\nSome text\n\n"
            "## Section B\n\n"
            "| C | D |\n"
            "|---|---|\n"
            "| 3 | 4 |\n"
        ))
        result = json.loads(context_list_tables("multi"))
        assert len(result) == 2

    def test_list_tables_no_tables(self, store):
        set_store(store)
        store.set_knowledge("plain", "Just text, no tables here.")
        result = json.loads(context_list_tables("plain"))
        assert result == []

    def test_list_tables_entry_not_found(self, store):
        set_store(store)
        result = json.loads(context_list_tables("nonexistent"))
        assert "error" in result
