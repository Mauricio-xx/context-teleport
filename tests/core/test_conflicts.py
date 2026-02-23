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


class TestConflictEntrySerialization:
    def test_to_full_dict_includes_all_content(self):
        entry = ConflictEntry(
            file_path="knowledge/arch.md",
            ours_content="Full ours content here",
            theirs_content="Full theirs content here",
            base_content="Full base content",
        )
        d = entry.to_full_dict()
        assert d["ours_content"] == "Full ours content here"
        assert d["theirs_content"] == "Full theirs content here"
        assert d["base_content"] == "Full base content"
        assert d["resolved"] is False
        assert d["resolution"] == ""

    def test_from_dict_round_trip(self):
        original = ConflictEntry(
            file_path="knowledge/stack.md",
            ours_content="Python 3.12",
            theirs_content="Python 3.11",
            base_content="Python 3.10",
            resolved=True,
            resolution="Python 3.12",
        )
        restored = ConflictEntry.from_dict(original.to_full_dict())
        assert restored.file_path == original.file_path
        assert restored.ours_content == original.ours_content
        assert restored.theirs_content == original.theirs_content
        assert restored.base_content == original.base_content
        assert restored.resolved == original.resolved
        assert restored.resolution == original.resolution

    def test_from_dict_defaults(self):
        entry = ConflictEntry.from_dict({
            "file_path": "test.md",
            "ours_content": "ours",
            "theirs_content": "theirs",
        })
        assert entry.base_content == ""
        assert entry.resolved is False
        assert entry.resolution == ""


class TestConflictReportSerialization:
    def test_conflict_id_generated(self):
        r1 = ConflictReport()
        r2 = ConflictReport()
        assert r1.conflict_id != r2.conflict_id
        assert len(r1.conflict_id) == 36  # UUID format

    def test_to_json_from_json_round_trip(self):
        original = ConflictReport(
            conflicts=[
                ConflictEntry("a.md", "ours-a", "theirs-a", "base-a"),
                ConflictEntry("b.md", "ours-b", "theirs-b", resolved=True, resolution="merged-b"),
            ],
            auto_resolved=["c.md"],
        )
        restored = ConflictReport.from_json(original.to_json())
        assert restored.conflict_id == original.conflict_id
        assert restored.auto_resolved == ["c.md"]
        assert len(restored.conflicts) == 2
        assert restored.conflicts[0].file_path == "a.md"
        assert restored.conflicts[0].ours_content == "ours-a"
        assert restored.conflicts[1].resolved is True
        assert restored.conflicts[1].resolution == "merged-b"

    def test_to_json_is_valid_json(self):
        import json
        report = ConflictReport(conflicts=[
            ConflictEntry("test.md", "ours", "theirs"),
        ])
        data = json.loads(report.to_json())
        assert "conflict_id" in data
        assert "conflicts" in data


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
