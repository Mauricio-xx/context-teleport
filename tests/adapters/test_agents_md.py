"""Tests for shared AGENTS.md parsing and writing utilities."""

from ctx.adapters._agents_md import (
    CTX_AGENTS_END,
    CTX_AGENTS_START,
    parse_agents_md,
    write_agents_md_section,
)


class TestParseAgentsMd:
    def test_parse_sections(self):
        text = "## Architecture\nHexagonal pattern\n\n## Conventions\nUse ruff\n"
        sections = parse_agents_md(text)
        assert len(sections) == 2
        assert sections[0][0] == "architecture"
        assert "Hexagonal" in sections[0][1]
        assert sections[1][0] == "conventions"

    def test_skips_managed_section(self):
        text = (
            "## Existing\nContent\n\n"
            f"{CTX_AGENTS_START}\n## Managed\nAuto content\n{CTX_AGENTS_END}\n\n"
            "## After\nMore content\n"
        )
        sections = parse_agents_md(text)
        keys = [s[0] for s in sections]
        assert "managed" not in keys
        assert "existing" in keys
        assert "after" in keys

    def test_no_headers_falls_back_to_h1(self):
        text = "# Main Title\nSome content\n"
        sections = parse_agents_md(text)
        assert len(sections) == 1
        assert sections[0][0] == "main-title"

    def test_no_headers_at_all(self):
        text = "Just plain text without any headers."
        sections = parse_agents_md(text)
        assert len(sections) == 1
        assert sections[0][0] == "agents"

    def test_empty_text(self):
        sections = parse_agents_md("")
        assert sections == []

    def test_only_managed_section(self):
        text = f"{CTX_AGENTS_START}\n## Managed\nContent\n{CTX_AGENTS_END}\n"
        sections = parse_agents_md(text)
        assert sections == []


class TestWriteAgentsMdSection:
    def test_write_into_empty(self):
        result = write_agents_md_section("", [("arch", "Architecture notes")])
        assert CTX_AGENTS_START in result
        assert CTX_AGENTS_END in result
        assert "### arch" in result
        assert "Architecture notes" in result

    def test_write_preserves_existing(self):
        existing = "## My Rules\nDo this and that.\n"
        result = write_agents_md_section(existing, [("arch", "Notes")])
        assert "My Rules" in result
        assert "Do this and that" in result
        assert CTX_AGENTS_START in result

    def test_replaces_existing_managed(self):
        existing = (
            "## Rules\nContent\n\n"
            f"{CTX_AGENTS_START}\n## Old\nOld content\n{CTX_AGENTS_END}\n"
        )
        result = write_agents_md_section(existing, [("new", "New content")])
        assert "Old content" not in result
        assert "New content" in result
        assert "Rules" in result

    def test_roundtrip(self):
        original = "## Existing\nKeep this.\n"
        entries = [("team-arch", "Architecture"), ("team-stack", "Python")]

        written = write_agents_md_section(original, entries)
        # Parse should not include managed section entries
        parsed = parse_agents_md(written)
        keys = [s[0] for s in parsed]
        assert "existing" in keys
        # Managed section entries should be skipped by parser
        assert "team-arch" not in keys

    def test_multiple_entries(self):
        result = write_agents_md_section(
            "",
            [
                ("arch", "Architecture"),
                ("stack", "Python + FastMCP"),
                ("conventions", "Use ruff"),
            ],
        )
        assert "### arch" in result
        assert "### stack" in result
        assert "### conventions" in result
