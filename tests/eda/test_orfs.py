"""Tests for ORFS config.mk parser."""

from __future__ import annotations

from pathlib import Path

import pytest

from ctx.eda.parsers.orfs import OrfsConfigParser


@pytest.fixture
def parser():
    return OrfsConfigParser()


@pytest.fixture
def simple_config(tmp_path: Path) -> Path:
    content = """\
export DESIGN_NAME = gcd
export PLATFORM    = ihp-sg13g2

export VERILOG_FILES = $(DESIGN_HOME)/src/$(DESIGN_NICKNAME)/gcd.v
export SDC_FILE      = $(DESIGN_HOME)/$(PLATFORM)/$(DESIGN_NICKNAME)/constraint.sdc

export USE_FILL = 1

export PLACE_DENSITY ?= 0.88
export CORE_UTILIZATION = 20
export TNS_END_PERCENT = 100
"""
    p = tmp_path / "config.mk"
    p.write_text(content)
    return p


@pytest.fixture
def config_with_continuations(tmp_path: Path) -> Path:
    content = """\
export DESIGN_NAME = uart
export PLATFORM = ihp-sg13g2

export ADDITIONAL_LEFS = $(wildcard $(DESIGN_HOME)/src/lefs/*.lef) \\
                         $(PLATFORM_DIR)/extra.lef

export DONT_USE_CELLS += sg13g2_fill_1 \\
    sg13g2_fill_2  # These cause DRC issues
"""
    p = tmp_path / "config.mk"
    p.write_text(content)
    return p


class TestCanParse:
    def test_valid_config(self, parser, simple_config):
        assert parser.can_parse(simple_config) is True

    def test_wrong_filename(self, parser, tmp_path):
        p = tmp_path / "Makefile"
        p.write_text("export DESIGN_NAME = x")
        assert parser.can_parse(p) is False

    def test_no_design_name(self, parser, tmp_path):
        p = tmp_path / "config.mk"
        p.write_text("SOME_VAR = value\n")
        assert parser.can_parse(p) is False

    def test_platform_only(self, parser, tmp_path):
        p = tmp_path / "config.mk"
        p.write_text("export PLATFORM = ihp-sg13g2\n")
        assert parser.can_parse(p) is True

    def test_nonexistent(self, parser, tmp_path):
        assert parser.can_parse(tmp_path / "config.mk") is False


class TestParse:
    def test_basic_extraction(self, parser, simple_config):
        items = parser.parse(simple_config)
        assert len(items) == 1
        assert items[0].key == "orfs-config-gcd"
        assert items[0].type == "knowledge"

    def test_platform_in_content(self, parser, simple_config):
        content = parser.parse(simple_config)[0].content
        assert "ihp-sg13g2" in content

    def test_variables_extracted(self, parser, simple_config):
        content = parser.parse(simple_config)[0].content
        assert "VERILOG_FILES" in content
        assert "PLACE_DENSITY" in content
        assert "CORE_UTILIZATION" in content

    def test_optional_operator(self, parser, simple_config):
        content = parser.parse(simple_config)[0].content
        assert "?=" in content  # PLACE_DENSITY uses ?=

    def test_line_continuation(self, parser, config_with_continuations):
        items = parser.parse(config_with_continuations)
        content = items[0].content
        assert "ADDITIONAL_LEFS" in content
        assert "extra.lef" in content

    def test_append_operator(self, parser, config_with_continuations):
        content = parser.parse(config_with_continuations)[0].content
        assert "DONT_USE_CELLS" in content

    def test_inline_comment_preserved(self, parser, config_with_continuations):
        content = parser.parse(config_with_continuations)[0].content
        assert "DRC issues" in content

    def test_categorization(self, parser, simple_config):
        content = parser.parse(simple_config)[0].content
        assert "Process" in content or "Design" in content


class TestDescribe:
    def test_describe(self, parser):
        assert "config.mk" in parser.describe()
        assert "ORFS" in parser.describe()
