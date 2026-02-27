"""Tests for CLI convention commands and import conventions from file."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from ctx.cli.main import app
from ctx.core.store import ContextStore

runner = CliRunner()


@pytest.fixture
def store(tmp_git_repo):
    import os
    orig = os.getcwd()
    os.chdir(tmp_git_repo)
    s = ContextStore(tmp_git_repo)
    s.init(project_name="cli-conv-test")
    yield s
    os.chdir(orig)


class TestConventionList:
    def test_list_empty(self, store):
        result = runner.invoke(app, ["convention", "list"])
        assert result.exit_code == 0
        assert "No conventions yet" in result.output

    def test_list_with_entries(self, store):
        store.set_convention("git", "Use branches.")
        store.set_convention("env", "No sudo.")
        result = runner.invoke(app, ["convention", "list"])
        assert result.exit_code == 0
        assert "git" in result.output
        assert "env" in result.output

    def test_list_json(self, store):
        store.set_convention("git", "Use branches.")
        result = runner.invoke(app, ["convention", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["key"] == "git"


class TestConventionGet:
    def test_get_existing(self, store):
        store.set_convention("git", "Use feature branches.")
        result = runner.invoke(app, ["convention", "get", "git"])
        assert result.exit_code == 0
        assert "feature branches" in result.output

    def test_get_missing(self, store):
        result = runner.invoke(app, ["convention", "get", "missing"])
        assert result.exit_code == 1

    def test_get_json(self, store):
        store.set_convention("git", "Use branches.")
        result = runner.invoke(app, ["convention", "get", "git", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["key"] == "git"


class TestConventionAdd:
    def test_add_from_stdin(self, store):
        result = runner.invoke(app, ["convention", "add", "git"], input="Use feature branches.\n")
        assert result.exit_code == 0
        assert store.get_convention("git") is not None

    def test_add_from_file(self, store, tmp_path):
        f = tmp_path / "conv.md"
        f.write_text("Always use venvs.\n")
        result = runner.invoke(app, ["convention", "add", "env", "--file", str(f)])
        assert result.exit_code == 0
        entry = store.get_convention("env")
        assert entry is not None
        assert "venvs" in entry.content

    def test_add_json(self, store):
        result = runner.invoke(
            app, ["convention", "add", "git", "--format", "json"],
            input="Use branches.\n",
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "written"


class TestConventionRm:
    def test_rm_existing(self, store):
        store.set_convention("git", "content")
        result = runner.invoke(app, ["convention", "rm", "git"])
        assert result.exit_code == 0
        assert store.get_convention("git") is None

    def test_rm_missing(self, store):
        result = runner.invoke(app, ["convention", "rm", "missing"])
        assert result.exit_code == 1


class TestConventionScope:
    def test_scope_change(self, store):
        store.set_convention("git", "content")
        result = runner.invoke(app, ["convention", "scope", "git", "private"])
        assert result.exit_code == 0
        from ctx.core.scope import Scope
        assert store.get_convention_scope("git") == Scope.private

    def test_scope_invalid(self, store):
        store.set_convention("git", "content")
        result = runner.invoke(app, ["convention", "scope", "git", "invalid"])
        assert result.exit_code == 1

    def test_scope_missing_entry(self, store):
        result = runner.invoke(app, ["convention", "scope", "missing", "public"])
        assert result.exit_code == 1


class TestImportConventions:
    def test_import_splits_by_h2(self, store, tmp_path):
        f = tmp_path / "rules.md"
        f.write_text("# My Rules\n\n## Git\n\nUse branches.\n\n## Environment\n\nNo sudo.\n")
        result = runner.invoke(app, ["import", "conventions", str(f)])
        assert result.exit_code == 0
        assert "2 convention" in result.output
        assert store.get_convention("git") is not None
        assert store.get_convention("environment") is not None

    def test_import_falls_back_to_h1(self, store, tmp_path):
        f = tmp_path / "rules.md"
        f.write_text("# Title\n\n# Git\n\nUse branches.\n\n# Env\n\nNo sudo.\n")
        result = runner.invoke(app, ["import", "conventions", str(f)])
        assert result.exit_code == 0
        assert store.get_convention("git") is not None
        assert store.get_convention("env") is not None

    def test_import_no_headers(self, store, tmp_path):
        f = tmp_path / "rules.md"
        f.write_text("Just a plain text convention.\n")
        result = runner.invoke(app, ["import", "conventions", str(f)])
        assert result.exit_code == 0
        assert store.get_convention("conventions") is not None

    def test_import_dry_run(self, store, tmp_path):
        f = tmp_path / "rules.md"
        f.write_text("## Git\n\nUse branches.\n")
        result = runner.invoke(app, ["import", "conventions", str(f), "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert store.get_convention("git") is None

    def test_import_json_format(self, store, tmp_path):
        f = tmp_path / "rules.md"
        f.write_text("## Git\n\nUse branches.\n")
        result = runner.invoke(app, ["import", "conventions", str(f), "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["imported"] == 1

    def test_import_missing_file(self, store):
        result = runner.invoke(app, ["import", "conventions", "/nonexistent/file.md"])
        assert result.exit_code == 1

    def test_import_with_scope(self, store, tmp_path):
        f = tmp_path / "rules.md"
        f.write_text("## Git\n\nUse branches.\n")
        result = runner.invoke(app, ["import", "conventions", str(f), "--scope", "private"])
        assert result.exit_code == 0
        from ctx.core.scope import Scope
        assert store.get_convention_scope("git") == Scope.private


class TestStatusIncludesConventions:
    def test_status_shows_convention_count(self, store):
        store.set_convention("git", "branches")
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Conventions" in result.output
