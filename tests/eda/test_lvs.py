"""Tests for Netgen LVS report parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from ctx.eda.parsers.lvs import NetgenLvsParser


@pytest.fixture
def parser():
    return NetgenLvsParser()


@pytest.fixture
def matching_report(tmp_path: Path) -> Path:
    """LVS report where circuits match."""
    d = tmp_path / "designs" / "counter" / "67-netgen-lvs" / "reports"
    d.mkdir(parents=True)
    content = """\
Cell sg13g2_decap_8 (0) disconnected node: VDD
Cell sg13g2_decap_8 (0) disconnected node: VSS

Subcircuit pins:
Circuit 1: sg13g2_decap_8                  |Circuit 2: sg13g2_decap_8
-------------------------------------------|-------------------------------------------
VDD                                        |VDD
VSS                                        |VSS
---------------------------------------------------------------------------------------
Cell pin lists are equivalent.
Device classes sg13g2_decap_8 and sg13g2_decap_8 are equivalent.

Subcircuit summary:
Circuit 1: counter                         |Circuit 2: counter
-------------------------------------------|-------------------------------------------
Number of devices: 27                      |Number of devices: 27
Number of nets: 27                         |Number of nets: 27
---------------------------------------------------------------------------------------
Netlists match uniquely.

Device classes counter and counter are equivalent.

Final result: Circuits match uniquely.
"""
    p = d / "lvs.netgen.rpt"
    p.write_text(content)
    return p


@pytest.fixture
def failing_report(tmp_path: Path) -> Path:
    """LVS report with mismatches."""
    d = tmp_path / "designs" / "mux" / "reports"
    d.mkdir(parents=True)
    content = """\
Device classes sg13g2_inv and sg13g2_inv are equivalent.
Device classes mux_core and mux_core are NOT equivalent.

Subcircuit summary:
Circuit 1: mux_core                        |Circuit 2: mux_core
-------------------------------------------|-------------------------------------------
Number of devices: 15                      |Number of devices: 12
Number of nets: 20                         |Number of nets: 18
---------------------------------------------------------------------------------------

Final result: Circuits do not match.
"""
    p = d / "lvs.netgen.rpt"
    p.write_text(content)
    return p


class TestCanParse:
    def test_valid_rpt(self, parser, matching_report):
        assert parser.can_parse(matching_report) is True

    def test_lvs_json(self, parser, tmp_path):
        p = tmp_path / "lvs.netgen.json"
        p.write_text("{}")
        assert parser.can_parse(p) is True

    def test_directory_with_lvs(self, parser, tmp_path):
        d = tmp_path / "netgen-lvs"
        d.mkdir()
        assert parser.can_parse(d) is True

    def test_non_lvs_rpt(self, parser, tmp_path):
        p = tmp_path / "timing.rpt"
        p.write_text("timing report")
        assert parser.can_parse(p) is False

    def test_nonexistent(self, parser, tmp_path):
        assert parser.can_parse(tmp_path / "no.rpt") is False


class TestParse:
    def test_matching_result(self, parser, matching_report):
        items = parser.parse(matching_report)
        assert len(items) == 1
        item = items[0]
        assert item.key == "lvs-summary-counter"
        assert "Circuits match uniquely" in item.content

    def test_device_counts(self, parser, matching_report):
        content = parser.parse(matching_report)[0].content
        assert "27" in content

    def test_cell_equivalence(self, parser, matching_report):
        content = parser.parse(matching_report)[0].content
        assert "Equivalent" in content
        assert "sg13g2_decap_8" in content or "counter" in content

    def test_failing_result(self, parser, failing_report):
        items = parser.parse(failing_report)
        assert len(items) == 1
        content = items[0].content
        assert "do not match" in content

    def test_mismatch_detected(self, parser, failing_report):
        content = parser.parse(failing_report)[0].content
        assert "Not equivalent" in content or "MISMATCH" in content

    def test_warnings_for_disconnected(self, parser, matching_report):
        content = parser.parse(matching_report)[0].content
        assert "disconnected" in content.lower() or "Warning" in content

    def test_directory_parse(self, parser, matching_report):
        # Parse the directory instead of the file
        rpt_dir = matching_report.parent.parent  # 67-netgen-lvs
        items = parser.parse(rpt_dir)
        assert len(items) == 1


class TestDescribe:
    def test_describe(self, parser):
        assert "LVS" in parser.describe()
        assert "Netgen" in parser.describe()
