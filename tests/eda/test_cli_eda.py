"""CLI integration tests for EDA import."""

from __future__ import annotations

import json
import os
from pathlib import Path

import git
import pytest
from typer.testing import CliRunner

from ctx.cli.main import app
from ctx.core.store import ContextStore

runner = CliRunner()


@pytest.fixture
def project_dir(tmp_path: Path):
    """Create a git repo and chdir into it."""
    repo = git.Repo.init(tmp_path)
    readme = tmp_path / "README.md"
    readme.write_text("# Test\n")
    repo.index.add(["README.md"])
    repo.index.commit("initial")
    original = os.getcwd()
    os.chdir(tmp_path)
    yield tmp_path
    os.chdir(original)


@pytest.fixture
def initialized_project(project_dir: Path) -> Path:
    """Project with context store initialized."""
    result = runner.invoke(app, ["init", "--name", "test-eda"])
    assert result.exit_code == 0
    return project_dir


@pytest.fixture
def librelane_config(initialized_project: Path) -> Path:
    data = {
        "meta": {"version": 2, "flow": ["Yosys.Synthesis", "Magic.DRC"]},
        "DESIGN_NAME": "inverter",
        "VERILOG_FILES": "dir::src/*.v",
        "FP_PDN_VPITCH": 25,
    }
    p = initialized_project / "config.json"
    p.write_text(json.dumps(data))
    return p


@pytest.fixture
def orfs_config(initialized_project: Path) -> Path:
    content = "export DESIGN_NAME = gcd\nexport PLATFORM = ihp-sg13g2\n"
    p = initialized_project / "config.mk"
    p.write_text(content)
    return p


class TestImportEda:
    def test_import_librelane_config(self, initialized_project, librelane_config):
        result = runner.invoke(app, ["import", "eda", str(librelane_config)], catch_exceptions=False)
        assert result.exit_code == 0
        assert "Imported" in result.output
        assert "librelane-config" in result.output

        store = ContextStore(initialized_project)
        entry = store.get_knowledge("librelane-config-inverter")
        assert entry is not None
        assert "inverter" in entry.content

    def test_import_dry_run(self, initialized_project, librelane_config):
        result = runner.invoke(
            app, ["import", "eda", str(librelane_config), "--dry-run"], catch_exceptions=False
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "librelane-config-inverter" in result.output

        store = ContextStore(initialized_project)
        assert store.get_knowledge("librelane-config-inverter") is None

    def test_import_json_format(self, initialized_project, librelane_config):
        result = runner.invoke(
            app, ["import", "eda", str(librelane_config), "--format", "json"], catch_exceptions=False
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["imported"] == 1
        assert data["importer"] == "librelane-config"

    def test_import_with_type_flag(self, initialized_project, orfs_config):
        result = runner.invoke(
            app, ["import", "eda", str(orfs_config), "--type", "orfs-config"], catch_exceptions=False
        )
        assert result.exit_code == 0
        assert "Imported" in result.output

    def test_import_wrong_type(self, initialized_project, librelane_config):
        result = runner.invoke(
            app, ["import", "eda", str(librelane_config), "--type", "orfs-config"]
        )
        assert result.exit_code == 1
        assert "cannot parse" in result.output

    def test_import_unknown_type(self, initialized_project, librelane_config):
        result = runner.invoke(
            app, ["import", "eda", str(librelane_config), "--type", "nonexistent"]
        )
        assert result.exit_code == 1
        assert "Unknown importer" in result.output

    def test_import_nonexistent_path(self, initialized_project):
        result = runner.invoke(app, ["import", "eda", "/nonexistent/path"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_import_unrecognized_file(self, initialized_project):
        p = initialized_project / "random.txt"
        p.write_text("just some text")
        result = runner.invoke(app, ["import", "eda", str(p)])
        assert result.exit_code == 1
        assert "No importer" in result.output

    def test_reimport_overwrites(self, initialized_project, librelane_config):
        """Reimporting the same file overwrites the knowledge entry."""
        runner.invoke(app, ["import", "eda", str(librelane_config)], catch_exceptions=False)

        data = json.loads(librelane_config.read_text())
        data["FP_PDN_VPITCH"] = 50
        librelane_config.write_text(json.dumps(data))

        runner.invoke(app, ["import", "eda", str(librelane_config)], catch_exceptions=False)

        store = ContextStore(initialized_project)
        entry = store.get_knowledge("librelane-config-inverter")
        assert "50" in entry.content


class TestInitEdaDetection:
    def test_init_shows_eda_info(self, project_dir):
        data = {"meta": {"version": 2}, "DESIGN_NAME": "inv", "VERILOG_FILES": "*.v"}
        (project_dir / "config.json").write_text(json.dumps(data))

        result = runner.invoke(app, ["init"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "EDA project detected" in result.output
        assert "librelane" in result.output

    def test_init_no_eda(self, project_dir):
        result = runner.invoke(app, ["init"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "EDA project detected" not in result.output
