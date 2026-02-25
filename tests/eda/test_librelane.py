"""Tests for LibreLane config.json parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ctx.eda.parsers.librelane import LibreLaneConfigParser


@pytest.fixture
def parser():
    return LibreLaneConfigParser()


@pytest.fixture
def simple_config(tmp_path: Path) -> Path:
    """Minimal LibreLane config (inverter-style)."""
    data = {
        "meta": {"version": 2, "flow": ["Yosys.Synthesis", "OpenROAD.Floorplan", "Magic.DRC"]},
        "DESIGN_NAME": "inverter",
        "VERILOG_FILES": "dir::src/*.v",
        "CLOCK_PORT": None,
        "FP_SIZING": "absolute",
        "DIE_AREA": [0, 0, 50, 50],
        "PL_TARGET_DENSITY_PCT": 75,
        "FP_PDN_VPITCH": 25,
        "FP_PDN_HPITCH": 25,
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture
def complex_config(tmp_path: Path) -> Path:
    """Config with PDK overrides and timing."""
    data = {
        "meta": {"version": 2},
        "DESIGN_NAME": "APU",
        "VERILOG_FILES": "dir::src/APU.v",
        "CLOCK_PORT": "clk",
        "CLOCK_PERIOD": 17,
        "FP_CORE_UTIL": 35,
        "pdk::sky130*": {"SYNTH_MAX_FANOUT": 6},
        "pdk::ihp-sg13g2*": {"CLOCK_PERIOD": 20, "FP_CORE_UTIL": 25},
    }
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data))
    return p


class TestCanParse:
    def test_valid_config(self, parser, simple_config):
        assert parser.can_parse(simple_config) is True

    def test_wrong_filename(self, parser, tmp_path):
        p = tmp_path / "settings.json"
        p.write_text(json.dumps({"meta": {"version": 2}, "DESIGN_NAME": "x"}))
        assert parser.can_parse(p) is False

    def test_missing_design_name(self, parser, tmp_path):
        p = tmp_path / "config.json"
        p.write_text(json.dumps({"meta": {"version": 2}}))
        assert parser.can_parse(p) is False

    def test_wrong_version(self, parser, tmp_path):
        p = tmp_path / "config.json"
        p.write_text(json.dumps({"meta": {"version": 1}, "DESIGN_NAME": "x"}))
        assert parser.can_parse(p) is False

    def test_version_3(self, parser, tmp_path):
        p = tmp_path / "config.json"
        p.write_text(json.dumps({"meta": {"version": 3}, "DESIGN_NAME": "x"}))
        assert parser.can_parse(p) is True

    def test_invalid_json(self, parser, tmp_path):
        p = tmp_path / "config.json"
        p.write_text("not json")
        assert parser.can_parse(p) is False

    def test_nonexistent(self, parser, tmp_path):
        assert parser.can_parse(tmp_path / "config.json") is False


class TestParse:
    def test_simple_produces_one_item(self, parser, simple_config):
        items = parser.parse(simple_config)
        assert len(items) == 1
        assert items[0].key == "librelane-config-inverter"
        assert items[0].type == "knowledge"

    def test_content_has_design_name(self, parser, simple_config):
        items = parser.parse(simple_config)
        assert "inverter" in items[0].content

    def test_content_has_flow_stages(self, parser, simple_config):
        content = parser.parse(simple_config)[0].content
        assert "Yosys.Synthesis" in content
        assert "Flow Stages" in content

    def test_content_has_physical_config(self, parser, simple_config):
        content = parser.parse(simple_config)[0].content
        assert "DIE_AREA" in content
        assert "0, 0, 50, 50" in content

    def test_content_has_pdn(self, parser, simple_config):
        content = parser.parse(simple_config)[0].content
        assert "FP_PDN_VPITCH" in content

    def test_pdk_overrides(self, parser, complex_config):
        content = parser.parse(complex_config)[0].content
        assert "pdk::sky130*" in content
        assert "SYNTH_MAX_FANOUT" in content
        assert "pdk::ihp-sg13g2*" in content

    def test_key_slug(self, parser, complex_config):
        items = parser.parse(complex_config)
        assert items[0].key == "librelane-config-apu"

    def test_source_is_path(self, parser, simple_config):
        items = parser.parse(simple_config)
        assert str(simple_config) in items[0].source


class TestDescribe:
    def test_describe(self, parser):
        assert "LibreLane" in parser.describe()
        assert "config.json" in parser.describe()
