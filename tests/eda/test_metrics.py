"""Tests for LibreLane metrics (state_in.json) parser."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ctx.eda.parsers.metrics import LibreLaneMetricsParser


@pytest.fixture
def parser():
    return LibreLaneMetricsParser()


@pytest.fixture
def metrics_file(tmp_path: Path) -> Path:
    data = {
        "json_h": f"{tmp_path}/designs/counter/runs/RUN/05-yosys/counter.h.json",
        "nl": f"{tmp_path}/designs/counter/runs/RUN/06-yosys/counter.nl.v",
        "metrics": {
            "design__instance__count": 10,
            "design__instance__area": 261.2736,
            "design__instance_unmapped__count": 0,
            "design__lint_error__count": 0,
            "synthesis__check_error__count": 0,
        },
    }
    p = tmp_path / "state_in.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture
def metrics_with_timing(tmp_path: Path) -> Path:
    data = {
        "metrics": {
            "design__instance__count": 500,
            "timing__setup__wns": -0.15,
            "timing__setup__tns": -1.23,
            "timing__hold__wns": 0.0,
            "drc__count": 42,
            "route__wirelength": 12345.6,
            "power__total": 0.0012,
        },
    }
    p = tmp_path / "designs" / "chip" / "runs" / "RUN_1" / "12-sta" / "state_in.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps(data))
    return p


@pytest.fixture
def run_directory(tmp_path: Path) -> Path:
    """Run directory with multiple state_in.json files."""
    run_dir = tmp_path / "designs" / "mux" / "runs" / "RUN_1"

    # Synthesis metrics
    d1 = run_dir / "06-yosys-synthesis"
    d1.mkdir(parents=True)
    (d1 / "state_in.json").write_text(
        json.dumps({"metrics": {"design__instance__count": 100}})
    )

    # Timing metrics
    d2 = run_dir / "12-openroad-staprepnr"
    d2.mkdir(parents=True)
    (d2 / "state_in.json").write_text(
        json.dumps({"metrics": {"timing__setup__wns": -0.5}})
    )

    # Non-metrics file (should be skipped)
    d3 = run_dir / "01-lint"
    d3.mkdir(parents=True)
    (d3 / "state_in.json").write_text(json.dumps({"status": "ok"}))

    return run_dir


class TestCanParse:
    def test_valid_file(self, parser, metrics_file):
        assert parser.can_parse(metrics_file) is True

    def test_no_metrics_key(self, parser, tmp_path):
        p = tmp_path / "state_in.json"
        p.write_text(json.dumps({"status": "ok"}))
        assert parser.can_parse(p) is False

    def test_not_state_in(self, parser, tmp_path):
        p = tmp_path / "other.json"
        p.write_text(json.dumps({"metrics": {"x": 1}}))
        assert parser.can_parse(p) is False

    def test_directory_with_metrics(self, parser, run_directory):
        assert parser.can_parse(run_directory) is True

    def test_empty_directory(self, parser, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        assert parser.can_parse(d) is False


class TestParse:
    def test_single_file(self, parser, metrics_file):
        items = parser.parse(metrics_file)
        assert len(items) == 1
        assert items[0].key == "eda-metrics-counter"
        assert "design__instance__count" in items[0].content
        assert "261" in items[0].content

    def test_timing_categorization(self, parser, metrics_with_timing):
        items = parser.parse(metrics_with_timing)
        assert len(items) == 1
        content = items[0].content
        assert "Timing" in content
        assert "DRC" in content
        assert "Routing" in content
        assert "Power" in content

    def test_directory_merges_metrics(self, parser, run_directory):
        items = parser.parse(run_directory)
        assert len(items) == 1
        content = items[0].content
        assert "design__instance__count" in content
        assert "timing__setup__wns" in content
        assert items[0].key == "eda-metrics-mux"

    def test_design_name_from_path(self, parser, metrics_with_timing):
        items = parser.parse(metrics_with_timing)
        assert items[0].key == "eda-metrics-chip"


class TestDescribe:
    def test_describe(self, parser):
        assert "state_in.json" in parser.describe()
