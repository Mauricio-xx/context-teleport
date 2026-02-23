"""Tests for section-level markdown merge logic."""

from ctx.core.merge_sections import (
    merge_markdown_sections,
    parse_sections,
    _normalize_header,
)


class TestParseSections:
    def test_no_headers(self):
        text = "Just plain text\nwith multiple lines."
        sections = parse_sections(text)
        assert len(sections) == 1
        assert sections[0].header == ""
        assert sections[0].content == text

    def test_preamble_and_sections(self):
        text = "Preamble here.\n\n## Alpha\nAlpha content.\n\n## Beta\nBeta content.\n"
        sections = parse_sections(text)
        assert len(sections) == 3
        assert sections[0].header == ""
        assert "Preamble" in sections[0].content
        assert sections[1].header == "## Alpha"
        assert "Alpha content." in sections[1].content
        assert sections[2].header == "## Beta"
        assert "Beta content." in sections[2].content

    def test_no_preamble(self):
        text = "## First\nContent one.\n## Second\nContent two.\n"
        sections = parse_sections(text)
        # No preamble when text starts with ##
        assert len(sections) == 2
        assert sections[0].header == "## First"
        assert sections[1].header == "## Second"

    def test_ignores_h3_headers(self):
        text = "## Main\nSome text.\n### Subsection\nMore text.\n"
        sections = parse_sections(text)
        # ### should not split -- only ## does
        h2_sections = [s for s in sections if s.header.startswith("## ")]
        assert len(h2_sections) == 1
        assert "### Subsection" in h2_sections[0].content


class TestNormalizeHeader:
    def test_basic(self):
        assert _normalize_header("## Backend") == "backend"

    def test_extra_whitespace(self):
        assert _normalize_header("##   Design  ") == "design"

    def test_empty(self):
        assert _normalize_header("") == ""


class TestMergeMarkdownSections:
    def test_identical_files(self):
        text = "## Intro\nHello.\n\n## Details\nWorld.\n"
        result = merge_markdown_sections(text, text, text)
        assert not result.has_conflicts
        assert result.content == text

    def test_no_changes_from_base(self):
        base = "## A\nBase content.\n"
        result = merge_markdown_sections(base, base, base)
        assert not result.has_conflicts
        assert result.content == base

    def test_only_ours_changed(self):
        base = "## A\nOriginal.\n## B\nOriginal.\n"
        ours = "## A\nModified by us.\n## B\nOriginal.\n"
        theirs = "## A\nOriginal.\n## B\nOriginal.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        assert "Modified by us." in result.content
        assert "Original." in result.content

    def test_only_theirs_changed(self):
        base = "## A\nOriginal.\n## B\nOriginal.\n"
        ours = "## A\nOriginal.\n## B\nOriginal.\n"
        theirs = "## A\nOriginal.\n## B\nChanged by them.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        assert "Changed by them." in result.content

    def test_different_sections_edited(self):
        base = "## A\nOriginal A.\n## B\nOriginal B.\n"
        ours = "## A\nOurs A.\n## B\nOriginal B.\n"
        theirs = "## A\nOriginal A.\n## B\nTheirs B.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        assert "Ours A." in result.content
        assert "Theirs B." in result.content

    def test_same_section_same_change(self):
        base = "## A\nOriginal.\n"
        ours = "## A\nIdentical change.\n"
        theirs = "## A\nIdentical change.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        assert "Identical change." in result.content

    def test_same_section_different_change_conflict(self):
        base = "## A\nOriginal.\n"
        ours = "## A\nOurs version.\n"
        theirs = "## A\nTheirs version.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert result.has_conflicts
        assert len(result.conflict_details) == 1
        assert "## A" in result.conflict_details[0]
        # Defaults to ours
        assert "Ours version." in result.content
        assert "Theirs version." not in result.content

    def test_section_added_by_ours(self):
        base = "## A\nContent.\n"
        ours = "## A\nContent.\n## New\nAdded by us.\n"
        theirs = "## A\nContent.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        assert "## New" in result.content
        assert "Added by us." in result.content

    def test_section_added_by_theirs(self):
        base = "## A\nContent.\n"
        ours = "## A\nContent.\n"
        theirs = "## A\nContent.\n## Extra\nAdded by them.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        assert "## Extra" in result.content
        assert "Added by them." in result.content

    def test_section_added_by_both_same_content(self):
        base = "## A\nContent.\n"
        ours = "## A\nContent.\n## Shared\nSame stuff.\n"
        theirs = "## A\nContent.\n## Shared\nSame stuff.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        assert "## Shared" in result.content

    def test_section_added_by_both_different_content(self):
        base = "## A\nContent.\n"
        ours = "## A\nContent.\n## Shared\nOurs stuff.\n"
        theirs = "## A\nContent.\n## Shared\nTheirs stuff.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert result.has_conflicts
        assert any("Shared" in d for d in result.conflict_details)
        # Defaults to ours
        assert "Ours stuff." in result.content

    def test_section_deleted_by_theirs_unchanged_by_ours(self):
        base = "## A\nKeep.\n## B\nRemove me.\n"
        ours = "## A\nKeep.\n## B\nRemove me.\n"
        theirs = "## A\nKeep.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        assert "## B" not in result.content
        assert "Remove me." not in result.content

    def test_section_deleted_by_ours_unchanged_by_theirs(self):
        base = "## A\nKeep.\n## B\nRemove me.\n"
        ours = "## A\nKeep.\n"
        theirs = "## A\nKeep.\n## B\nRemove me.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        assert "## B" not in result.content

    def test_section_deleted_by_theirs_modified_by_ours(self):
        base = "## A\nKeep.\n## B\nOriginal.\n"
        ours = "## A\nKeep.\n## B\nModified by us.\n"
        theirs = "## A\nKeep.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert result.has_conflicts
        assert any("## B" in d for d in result.conflict_details)
        # Ours version kept on delete-modify conflict
        assert "Modified by us." in result.content

    def test_section_deleted_by_ours_modified_by_theirs(self):
        base = "## A\nKeep.\n## B\nOriginal.\n"
        ours = "## A\nKeep.\n"
        theirs = "## A\nKeep.\n## B\nModified by them.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert result.has_conflicts
        assert any("## B" in d for d in result.conflict_details)
        # Theirs version kept since ours deleted it
        assert "Modified by them." in result.content

    def test_preamble_change(self):
        base = "Preamble.\n\n## A\nContent.\n"
        ours = "Updated preamble.\n\n## A\nContent.\n"
        theirs = "Preamble.\n\n## A\nContent.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        assert "Updated preamble." in result.content

    def test_preamble_conflict(self):
        base = "Preamble.\n\n## A\nContent.\n"
        ours = "Ours preamble.\n\n## A\nContent.\n"
        theirs = "Theirs preamble.\n\n## A\nContent.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert result.has_conflicts
        assert any("preamble" in d for d in result.conflict_details)
        assert "Ours preamble." in result.content

    def test_empty_files(self):
        result = merge_markdown_sections("", "", "")
        assert not result.has_conflicts
        assert result.content == ""

    def test_no_headers_fallback_identical(self):
        text = "Plain text, no headers."
        result = merge_markdown_sections(text, text, text)
        assert not result.has_conflicts
        assert result.content == text

    def test_no_headers_fallback_one_side_changed(self):
        base = "Original plain text."
        ours = "Modified plain text."
        theirs = "Original plain text."
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        assert result.content == "Modified plain text."

    def test_no_headers_fallback_conflict(self):
        base = "Original."
        ours = "Ours version."
        theirs = "Theirs version."
        result = merge_markdown_sections(base, ours, theirs)
        assert result.has_conflicts
        assert "Whole-file conflict" in result.conflict_details[0]
        assert result.content == "Ours version."

    def test_multiple_sections_mixed_changes(self):
        base = (
            "## Intro\nIntro base.\n"
            "## Backend\nBackend base.\n"
            "## Frontend\nFrontend base.\n"
            "## Deploy\nDeploy base.\n"
        )
        ours = (
            "## Intro\nIntro ours.\n"        # modified
            "## Backend\nBackend base.\n"      # unchanged
            "## Frontend\nFrontend base.\n"    # unchanged
            "## Deploy\nDeploy base.\n"        # unchanged
            "## Logging\nNew from ours.\n"     # added
        )
        theirs = (
            "## Intro\nIntro base.\n"          # unchanged
            "## Backend\nBackend theirs.\n"    # modified
            # Frontend deleted
            "## Deploy\nDeploy base.\n"        # unchanged
            "## Monitoring\nNew from theirs.\n"  # added
        )
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        # Ours change taken for Intro
        assert "Intro ours." in result.content
        # Theirs change taken for Backend
        assert "Backend theirs." in result.content
        # Frontend deleted by theirs, unchanged by ours -- deleted
        assert "Frontend base." not in result.content
        # Deploy unchanged
        assert "Deploy base." in result.content
        # New sections from both sides included
        assert "## Logging" in result.content
        assert "## Monitoring" in result.content

    def test_order_preserved_base_then_ours_then_theirs(self):
        base = "## A\nA content.\n## B\nB content.\n"
        ours = "## A\nA content.\n## B\nB content.\n## C\nFrom ours.\n"
        theirs = "## A\nA content.\n## B\nB content.\n## D\nFrom theirs.\n"
        result = merge_markdown_sections(base, ours, theirs)
        assert not result.has_conflicts
        # C should appear before D (ours new sections first, then theirs)
        c_pos = result.content.index("## C")
        d_pos = result.content.index("## D")
        assert c_pos < d_pos
