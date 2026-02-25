"""Tests for Magic DRC report parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from ctx.eda.parsers.drc import MagicDrcParser


@pytest.fixture
def parser():
    return MagicDrcParser()


@pytest.fixture
def drc_report(tmp_path: Path) -> Path:
    """Realistic Magic DRC report."""
    d = tmp_path / "61-magic-drc" / "reports"
    d.mkdir(parents=True)
    content = """\
chip_top
----------------------------------------
This layer can't abut or partially overlap between subcells
----------------------------------------
 192.065um 31.405um 192.265um 31.620um
 191.935um 31.620um 192.265um 31.930um
 192.065um 31.480um 192.265um 31.620um
----------------------------------------
Metal2 minimum spacing violation
----------------------------------------
 100.000um 50.000um 100.200um 50.100um
 200.000um 60.000um 200.200um 60.100um
 300.000um 70.000um 300.200um 70.100um
 400.000um 80.000um 400.200um 80.100um
 500.000um 90.000um 500.200um 90.100um
[INFO] COUNT: 8
[INFO] Should be divided by 3 or 4
"""
    p = d / "drc.magic.rpt"
    p.write_text(content)
    return p


@pytest.fixture
def empty_drc(tmp_path: Path) -> Path:
    """DRC report with no violations."""
    d = tmp_path / "magic-drc" / "reports"
    d.mkdir(parents=True)
    p = d / "drc.magic.rpt"
    p.write_text("clean_design\n")
    return p


class TestCanParse:
    def test_valid_drc_report(self, parser, drc_report):
        assert parser.can_parse(drc_report) is True

    def test_wrong_extension(self, parser, tmp_path):
        p = tmp_path / "drc.txt"
        p.write_text("some text")
        assert parser.can_parse(p) is False

    def test_rpt_in_drc_dir(self, parser, tmp_path):
        d = tmp_path / "drc-check"
        d.mkdir()
        p = d / "report.rpt"
        p.write_text("design\n---\n")
        assert parser.can_parse(p) is True

    def test_drc_in_filename(self, parser, tmp_path):
        p = tmp_path / "drc_violations.rpt"
        p.write_text("design\n---\n")
        assert parser.can_parse(p) is True

    def test_nonexistent(self, parser, tmp_path):
        assert parser.can_parse(tmp_path / "no.rpt") is False

    def test_directory(self, parser, tmp_path):
        assert parser.can_parse(tmp_path) is False


class TestParse:
    def test_extracts_violations(self, parser, drc_report):
        items = parser.parse(drc_report)
        assert len(items) == 1
        item = items[0]
        assert item.key == "drc-summary-chip-top"
        assert item.type == "knowledge"

    def test_violation_counts(self, parser, drc_report):
        content = parser.parse(drc_report)[0].content
        # 3 violations for first rule, 5 for second
        assert "3" in content
        assert "5" in content
        assert "Total violations" in content
        assert "8" in content

    def test_rule_names(self, parser, drc_report):
        content = parser.parse(drc_report)[0].content
        assert "This layer can't abut" in content
        assert "Metal2 minimum spacing" in content

    def test_sorted_by_count(self, parser, drc_report):
        content = parser.parse(drc_report)[0].content
        # Metal2 (5) should come before abut (3) in the table
        metal2_pos = content.find("Metal2")
        abut_pos = content.find("abut")
        assert metal2_pos < abut_pos

    def test_empty_report(self, parser, empty_drc):
        items = parser.parse(empty_drc)
        assert len(items) == 1
        assert "0" in items[0].content

    def test_unique_rules_count(self, parser, drc_report):
        content = parser.parse(drc_report)[0].content
        assert "Unique rules" in content
        assert "2" in content


class TestDescribe:
    def test_describe(self, parser):
        assert "DRC" in parser.describe()
        assert "streaming" in parser.describe()
