"""Tests for conflict detection and resolution."""

from __future__ import annotations

from ctx.core.conflicts import (
    ConflictEntry,
    ConflictReport,
    Strategy,
    resolve_conflicts,
    resolve_single,
)
from ctx.core.merge import merge_json, merge_markdown


class TestConflictEntry:
    def test_to_dict(self):
        entry = ConflictEntry(
            file_path="knowledge/arch.md",
            ours_content="Our version",
            theirs_content="Their version",
        )
        d = entry.to_dict()
        assert d["file_path"] == "knowledge/arch.md"
        assert d["resolved"] is False

    def test_preview_truncation(self):
        entry = ConflictEntry(
            file_path="test.md",
            ours_content="x" * 500,
            theirs_content="y" * 500,
        )
        d = entry.to_dict()
        assert len(d["ours_preview"]) == 200
        assert len(d["theirs_preview"]) == 200


class TestConflictReport:
    def test_empty_report(self):
        report = ConflictReport()
        assert not report.has_conflicts
        assert report.unresolved_count == 0

    def test_with_unresolved(self):
        report = ConflictReport(conflicts=[
            ConflictEntry("a.md", "ours", "theirs"),
            ConflictEntry("b.md", "ours", "theirs"),
        ])
        assert report.has_conflicts
        assert report.unresolved_count == 2

    def test_mixed_resolved(self):
        report = ConflictReport(conflicts=[
            ConflictEntry("a.md", "ours", "theirs", resolved=True),
            ConflictEntry("b.md", "ours", "theirs"),
        ])
        assert report.has_conflicts
        assert report.unresolved_count == 1

    def test_to_dict(self):
        report = ConflictReport(
            conflicts=[ConflictEntry("a.md", "ours", "theirs")],
            auto_resolved=["b.md"],
        )
        d = report.to_dict()
        assert d["has_conflicts"] is True
        assert d["total"] == 1
        assert d["unresolved"] == 1
        assert d["auto_resolved"] == ["b.md"]


class TestResolveConflicts:
    def test_ours_strategy(self):
        report = ConflictReport(conflicts=[
            ConflictEntry("a.md", "local content", "remote content"),
        ])
        resolutions = resolve_conflicts(report, Strategy.ours)
        assert len(resolutions) == 1
        assert resolutions[0] == ("a.md", "local content")
        assert report.conflicts[0].resolved

    def test_theirs_strategy(self):
        report = ConflictReport(conflicts=[
            ConflictEntry("a.md", "local content", "remote content"),
        ])
        resolutions = resolve_conflicts(report, Strategy.theirs)
        assert len(resolutions) == 1
        assert resolutions[0] == ("a.md", "remote content")

    def test_interactive_does_nothing(self):
        report = ConflictReport(conflicts=[
            ConflictEntry("a.md", "local", "remote"),
        ])
        resolutions = resolve_conflicts(report, Strategy.interactive)
        assert resolutions == []
        assert not report.conflicts[0].resolved

    def test_agent_does_nothing(self):
        report = ConflictReport(conflicts=[
            ConflictEntry("a.md", "local", "remote"),
        ])
        resolutions = resolve_conflicts(report, Strategy.agent)
        assert resolutions == []

    def test_skips_already_resolved(self):
        report = ConflictReport(conflicts=[
            ConflictEntry("a.md", "local", "remote", resolved=True),
            ConflictEntry("b.md", "local2", "remote2"),
        ])
        resolutions = resolve_conflicts(report, Strategy.ours)
        assert len(resolutions) == 1
        assert resolutions[0][0] == "b.md"


class TestResolveSingle:
    def test_resolve_found(self):
        report = ConflictReport(conflicts=[
            ConflictEntry("a.md", "ours", "theirs"),
        ])
        result = resolve_single(report, "a.md", "merged content")
        assert result is True
        assert report.conflicts[0].resolved
        assert report.conflicts[0].resolution == "merged content"

    def test_resolve_not_found(self):
        report = ConflictReport(conflicts=[
            ConflictEntry("a.md", "ours", "theirs"),
        ])
        result = resolve_single(report, "b.md", "content")
        assert result is False


class TestMergeJsonWithStrategy:
    def test_ours_strategy(self):
        result = merge_json(
            {"key": "base"}, {"key": "ours"}, {"key": "theirs"}, strategy=Strategy.ours
        )
        assert result.has_conflicts
        assert result.content["key"] == "ours"

    def test_theirs_strategy(self):
        result = merge_json(
            {"key": "base"}, {"key": "ours"}, {"key": "theirs"}, strategy=Strategy.theirs
        )
        assert result.has_conflicts
        assert result.content["key"] == "theirs"


class TestMergeMarkdown:
    def test_identical(self):
        result = merge_markdown("same content", "same content")
        assert not result.has_conflicts
        assert result.content == "same content"

    def test_conflict_ours(self):
        result = merge_markdown("our version", "their version", strategy=Strategy.ours)
        assert result.has_conflicts
        assert result.content == "our version"

    def test_conflict_theirs(self):
        result = merge_markdown("our version", "their version", strategy=Strategy.theirs)
        assert result.has_conflicts
        assert result.content == "their version"
