"""CLI integration tests for GitHub issue import."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import git
import pytest
from typer.testing import CliRunner

from ctx.cli.main import app
from ctx.core.store import ContextStore

runner = CliRunner()


def _make_issue(
    number: int = 1,
    title: str = "Test issue",
    state: str = "OPEN",
    body: str = "Issue body with enough text.",
    author: str = "testuser",
    labels: list[str] | None = None,
    comments: list[dict] | None = None,
    closed_at: str = "",
) -> dict:
    return {
        "number": number,
        "title": title,
        "state": state,
        "body": body,
        "author": {"login": author},
        "authorAssociation": "CONTRIBUTOR",
        "labels": [{"name": lb} for lb in (labels or [])],
        "comments": comments or [],
        "createdAt": "2026-01-15T10:00:00Z",
        "closedAt": closed_at,
        "url": f"https://github.com/test/repo/issues/{number}",
    }


def _make_comment(author: str, body: str, association: str = "NONE") -> dict:
    return {
        "author": {"login": author},
        "body": body,
        "authorAssociation": association,
        "createdAt": "2026-01-16T10:00:00Z",
        "reactions": {"totalCount": 0},
    }


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
    result = runner.invoke(app, ["init", "--name", "test-gh"])
    assert result.exit_code == 0
    return project_dir


class TestImportGitHubCLI:
    def test_import_single_issue(self, initialized_project):
        issue = _make_issue(835, title="Abutment check for IO cells")
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issue), stderr=""
            )
            result = runner.invoke(
                app,
                ["import", "github", "--repo", "IHP-GmbH/IHP-Open-PDK", "--issue", "835"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "Imported" in result.output

        store = ContextStore(initialized_project)
        entry = store.get_knowledge("github-issue-ihp-gmbh-ihp-open-pdk-835")
        assert entry is not None
        assert "Abutment check" in entry.content

    def test_import_batch(self, initialized_project):
        issues = [_make_issue(1, title="First"), _make_issue(2, title="Second")]
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issues), stderr=""
            )
            result = runner.invoke(
                app,
                ["import", "github", "--repo", "owner/repo"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "Imported" in result.output

        store = ContextStore(initialized_project)
        assert store.get_knowledge("github-issue-owner-repo-1") is not None
        assert store.get_knowledge("github-issue-owner-repo-2") is not None

    def test_import_with_labels(self, initialized_project):
        issues = [_make_issue(1, labels=["DRC"])]
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issues), stderr=""
            )
            result = runner.invoke(
                app,
                ["import", "github", "--repo", "o/r", "--labels", "DRC,layout"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        cmd = mock_run.call_args[0][0]
        assert "--label" in cmd

    def test_import_as_decisions(self, initialized_project):
        comments = [
            _make_comment("dev", "Resolution: added guard rings to all pads, verified clean.", "MEMBER"),
        ]
        issue = _make_issue(
            10, title="Guard ring requirement", state="CLOSED",
            comments=comments, closed_at="2026-02-01T00:00:00Z",
        )
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issue), stderr=""
            )
            result = runner.invoke(
                app,
                [
                    "import", "github", "--repo", "o/r",
                    "--issue", "10", "--as-decisions",
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "decision" in result.output.lower()

        store = ContextStore(initialized_project)
        decisions = store.list_decisions()
        assert len(decisions) >= 1
        assert any("Guard ring" in d.title for d in decisions)

    def test_import_dry_run(self, initialized_project):
        issue = _make_issue(1)
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issue), stderr=""
            )
            result = runner.invoke(
                app,
                ["import", "github", "--repo", "o/r", "--issue", "1", "--dry-run"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "Dry run" in result.output

        store = ContextStore(initialized_project)
        assert store.get_knowledge("github-issue-o-r-1") is None

    def test_import_dry_run_json(self, initialized_project):
        issue = _make_issue(1)
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issue), stderr=""
            )
            result = runner.invoke(
                app,
                [
                    "import", "github", "--repo", "o/r",
                    "--issue", "1", "--dry-run", "--format", "json",
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["dry_run"] is True
        assert data["imported"] == 0
        assert len(data["items"]) >= 1

    def test_import_no_repo(self, initialized_project):
        """No --repo and no github remote should error."""
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="origin\thttps://gitlab.com/owner/repo.git (fetch)\n",
                stderr="",
            )
            result = runner.invoke(
                app,
                ["import", "github"],
                catch_exceptions=False,
            )

        assert result.exit_code == 1
        assert "Cannot detect" in result.output

    def test_import_auto_detect_repo(self, initialized_project):
        issue = _make_issue(1)
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            # First call: detect_repo (git remote -v)
            # Subsequent calls: gh issue list/view
            mock_run.side_effect = [
                MagicMock(
                    returncode=0,
                    stdout="origin\tgit@github.com:IHP-GmbH/IHP-Open-PDK.git (fetch)\n",
                    stderr="",
                ),
                MagicMock(
                    returncode=0, stdout=json.dumps(issue), stderr=""
                ),
            ]
            result = runner.invoke(
                app,
                ["import", "github", "--issue", "1"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "Auto-detected" in result.output

    def test_import_gh_not_found(self, initialized_project):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            # detect_repo succeeds but gh fails
            mock_run.side_effect = [
                MagicMock(
                    returncode=0,
                    stdout="origin\tgit@github.com:o/r.git (fetch)\n",
                    stderr="",
                ),
                FileNotFoundError,
            ]
            result = runner.invoke(
                app,
                ["import", "github"],
                catch_exceptions=False,
            )

        assert result.exit_code == 1
        assert "gh CLI not found" in result.output

    def test_import_no_results(self, initialized_project):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="[]", stderr=""
            )
            result = runner.invoke(
                app,
                ["import", "github", "--repo", "o/r"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        assert "No issues found" in result.output

    def test_import_limit(self, initialized_project):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="[]", stderr=""
            )
            runner.invoke(
                app,
                ["import", "github", "--repo", "o/r", "--limit", "5"],
                catch_exceptions=False,
            )

        cmd = mock_run.call_args[0][0]
        limit_idx = cmd.index("--limit")
        assert cmd[limit_idx + 1] == "5"

    def test_import_single_issue_json(self, initialized_project):
        issue = _make_issue(42, title="JSON test")
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issue), stderr=""
            )
            result = runner.invoke(
                app,
                [
                    "import", "github", "--repo", "o/r",
                    "--issue", "42", "--format", "json",
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["imported"] == 1
        assert data["knowledge"] == 1
