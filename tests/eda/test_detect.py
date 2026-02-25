"""Tests for EDA project detector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ctx.eda.detect import detect_eda_project


@pytest.fixture
def librelane_project(tmp_path: Path) -> Path:
    data = {
        "meta": {"version": 2},
        "DESIGN_NAME": "inverter",
        "VERILOG_FILES": "dir::src/*.v",
        "pdk::ihp-sg13g2*": {"FP_CORE_UTIL": 25},
    }
    (tmp_path / "config.json").write_text(json.dumps(data))
    return tmp_path


@pytest.fixture
def orfs_project(tmp_path: Path) -> Path:
    (tmp_path / "config.mk").write_text(
        "export DESIGN_NAME = gcd\nexport PLATFORM = ihp-sg13g2\n"
    )
    return tmp_path


@pytest.fixture
def pdk_project(tmp_path: Path) -> Path:
    (tmp_path / "libs.tech").mkdir()
    return tmp_path


@pytest.fixture
def analog_project(tmp_path: Path) -> Path:
    (tmp_path / "xschemrc").write_text("# xschem config\n")
    (tmp_path / "inverter.sch").write_text("")
    return tmp_path


class TestDetection:
    def test_librelane(self, librelane_project):
        info = detect_eda_project(librelane_project)
        assert info.detected is True
        assert info.project_type == "librelane"
        assert info.design_name == "inverter"
        assert "ihp-sg13g2" in info.pdk

    def test_orfs(self, orfs_project):
        info = detect_eda_project(orfs_project)
        assert info.detected is True
        assert info.project_type == "orfs"
        assert info.design_name == "gcd"
        assert info.pdk == "ihp-sg13g2"

    def test_pdk(self, pdk_project):
        info = detect_eda_project(pdk_project)
        assert info.detected is True
        assert info.project_type == "pdk"

    def test_analog(self, analog_project):
        info = detect_eda_project(analog_project)
        assert info.detected is True
        assert info.project_type == "analog"
        assert "xschemrc" in info.markers_found

    def test_empty_directory(self, tmp_path):
        info = detect_eda_project(tmp_path)
        assert info.detected is False
        assert info.project_type == ""


class TestSkillSuggestions:
    def test_librelane_skills(self, librelane_project):
        info = detect_eda_project(librelane_project)
        assert "configure-librelane" in info.suggested_skills
        assert "debug-drc" in info.suggested_skills
        assert "debug-timing" in info.suggested_skills

    def test_orfs_skills(self, orfs_project):
        info = detect_eda_project(orfs_project)
        assert "configure-pdn" in info.suggested_skills

    def test_pdk_skills(self, pdk_project):
        info = detect_eda_project(pdk_project)
        assert "port-design" in info.suggested_skills

    def test_analog_skills(self, analog_project):
        info = detect_eda_project(analog_project)
        assert "xschem-simulate" in info.suggested_skills
        assert "characterize-device" in info.suggested_skills


class TestMarkers:
    def test_multiple_markers(self, tmp_path):
        """Project with both LibreLane config and .sch files."""
        data = {
            "meta": {"version": 2},
            "DESIGN_NAME": "mixed",
            "VERILOG_FILES": "dir::src/*.v",
        }
        (tmp_path / "config.json").write_text(json.dumps(data))
        (tmp_path / "top.sch").write_text("")

        info = detect_eda_project(tmp_path)
        assert info.detected is True
        assert info.project_type == "librelane"  # librelane takes priority
        assert len(info.markers_found) >= 2

    def test_pdk_root_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PDK_ROOT", "/opt/pdk/ihp-sg13g2")
        (tmp_path / "libs.tech").mkdir()
        info = detect_eda_project(tmp_path)
        assert any("PDK_ROOT" in m for m in info.markers_found)


class TestPriority:
    def test_librelane_over_orfs(self, tmp_path):
        """If both config.json and config.mk exist, LibreLane wins."""
        data = {
            "meta": {"version": 2},
            "DESIGN_NAME": "top",
            "VERILOG_FILES": "dir::src/*.v",
        }
        (tmp_path / "config.json").write_text(json.dumps(data))
        (tmp_path / "config.mk").write_text("export DESIGN_NAME = top\nexport PLATFORM = x\n")

        info = detect_eda_project(tmp_path)
        assert info.project_type == "librelane"
        # But ORFS marker should still be recorded
        assert any("config.mk" in m for m in info.markers_found)
