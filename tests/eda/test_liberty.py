"""Tests for Liberty .lib header parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from ctx.eda.parsers.liberty import LibertyParser


@pytest.fixture
def parser():
    return LibertyParser()


@pytest.fixture
def single_lib(tmp_path: Path) -> Path:
    content = """\
/* Liberty file */
library (sg13g2_stdcell_typ_1p20V_25C) {
  comment : "IHP Microelectronics GmbH, 2025";
  delay_model : table_lookup;
  capacitive_load_unit (1,pf);
  current_unit : "1uA";
  leakage_power_unit : "1pW";
  time_unit : "1ns";
  voltage_unit : "1V";
  default_max_capacitance : 0.3;
  default_max_fanout : 8;
  default_max_transition : 2.5074;
  nom_process : 1;
  nom_temperature : 25;
  nom_voltage : 1.2;

  cell (sg13g2_inv_1) {
    /* cell definition follows */
  }
}
"""
    p = tmp_path / "sg13g2_stdcell_typ_1p20V_25C.lib"
    p.write_text(content)
    return p


@pytest.fixture
def lib_directory(tmp_path: Path) -> Path:
    """Directory with multiple Liberty files (different corners)."""
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()

    for corner, temp, voltage in [
        ("typ", 25, 1.2),
        ("ff", -40, 1.32),
        ("ss", 125, 1.08),
    ]:
        content = f"""\
library (sg13g2_stdcell_{corner}_{voltage:.2f}V_{temp}C) {{
  nom_process : 1;
  nom_temperature : {temp};
  nom_voltage : {voltage};
  time_unit : "1ns";
  voltage_unit : "1V";

  cell (inv) {{
  }}
}}
"""
        name = f"sg13g2_stdcell_{corner}_{str(voltage).replace('.', 'p')}V_{temp}C.lib"
        (lib_dir / name).write_text(content)

    return lib_dir


class TestCanParse:
    def test_single_lib(self, parser, single_lib):
        assert parser.can_parse(single_lib) is True

    def test_directory_with_libs(self, parser, lib_directory):
        assert parser.can_parse(lib_directory) is True

    def test_wrong_extension(self, parser, tmp_path):
        p = tmp_path / "file.txt"
        p.write_text("not a lib")
        assert parser.can_parse(p) is False

    def test_empty_directory(self, parser, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        assert parser.can_parse(d) is False


class TestParseSingle:
    def test_produces_one_item(self, parser, single_lib):
        items = parser.parse(single_lib)
        assert len(items) == 1
        assert items[0].type == "knowledge"

    def test_library_name(self, parser, single_lib):
        content = parser.parse(single_lib)[0].content
        assert "sg13g2_stdcell_typ_1p20V_25C" in content

    def test_pvt_values(self, parser, single_lib):
        content = parser.parse(single_lib)[0].content
        assert "1.2" in content  # voltage
        assert "25" in content  # temperature

    def test_units_extracted(self, parser, single_lib):
        content = parser.parse(single_lib)[0].content
        assert "time_unit" in content
        assert "1ns" in content

    def test_defaults_extracted(self, parser, single_lib):
        content = parser.parse(single_lib)[0].content
        assert "default_max_fanout" in content
        assert "8" in content

    def test_corner_inference(self, parser, single_lib):
        content = parser.parse(single_lib)[0].content
        assert "typical" in content.lower() or "typ" in content.lower()

    def test_key_has_family_name(self, parser, single_lib):
        items = parser.parse(single_lib)
        assert "sg13g2-stdcell" in items[0].key

    def test_stops_at_cell(self, parser, single_lib):
        """Parser should not include cell definition content."""
        content = parser.parse(single_lib)[0].content
        assert "sg13g2_inv_1" not in content


class TestParseDirectory:
    def test_produces_one_summary(self, parser, lib_directory):
        items = parser.parse(lib_directory)
        assert len(items) == 1

    def test_lists_all_corners(self, parser, lib_directory):
        content = parser.parse(lib_directory)[0].content
        assert "typ" in content
        assert "ff" in content
        assert "ss" in content

    def test_corner_count(self, parser, lib_directory):
        content = parser.parse(lib_directory)[0].content
        assert "3" in content

    def test_key_uses_family(self, parser, lib_directory):
        items = parser.parse(lib_directory)
        # Should strip corner suffixes to get family name
        assert "sg13g2-stdcell" in items[0].key


class TestDescribe:
    def test_describe(self, parser):
        assert "Liberty" in parser.describe()
        assert ".lib" in parser.describe()
