"""Unit tests for GitHub source importer.

All tests mock subprocess.run -- no real GitHub API calls.
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from ctx.sources.base import SourceConfig
from ctx.sources.github import (
    GitHubSource,
    GitHubSourceError,
    _clean_body,
    _format_date,
    _parse_github_remote,
    _repo_slug,
)


# -- Fixtures --


def _make_issue(
    number: int = 1,
    title: str = "Test issue",
    state: str = "OPEN",
    body: str = "Issue body text here.",
    author: str = "testuser",
    author_assoc: str = "CONTRIBUTOR",
    labels: list[str] | None = None,
    comments: list[dict] | None = None,
    created_at: str = "2026-01-15T10:00:00Z",
    closed_at: str = "",
    url: str = "",
) -> dict:
    """Build a mock issue dict matching gh JSON output."""
    return {
        "number": number,
        "title": title,
        "state": state,
        "body": body,
        "author": {"login": author},
        "authorAssociation": author_assoc,
        "labels": [{"name": lb} for lb in (labels or [])],
        "comments": comments or [],
        "createdAt": created_at,
        "closedAt": closed_at,
        "url": url or f"https://github.com/owner/repo/issues/{number}",
    }


def _make_comment(
    author: str = "commenter",
    body: str = "This is a comment with enough text.",
    association: str = "NONE",
    created_at: str = "2026-01-16T10:00:00Z",
    reactions: dict | None = None,
) -> dict:
    return {
        "author": {"login": author},
        "body": body,
        "authorAssociation": association,
        "createdAt": created_at,
        "reactions": reactions or {"totalCount": 0},
    }


@pytest.fixture
def source() -> GitHubSource:
    return GitHubSource()


@pytest.fixture
def default_config() -> SourceConfig:
    return SourceConfig(repo="IHP-GmbH/IHP-Open-PDK")


# -- fetch_issues tests --


class TestFetchIssues:
    def test_fetch_issues_basic(self, source: GitHubSource):
        issues = [_make_issue(1), _make_issue(2)]
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issues), stderr=""
            )
            result = source.fetch_issues(SourceConfig(repo="owner/repo"))

        assert len(result) == 2
        assert result[0]["number"] == 1
        # Verify basic flags
        cmd = mock_run.call_args[0][0]
        assert "--repo" in cmd
        assert "owner/repo" in cmd
        assert "--json" in cmd

    def test_fetch_issues_with_labels(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="[]", stderr=""
            )
            source.fetch_issues(
                SourceConfig(repo="o/r", labels=["DRC", "layout"])
            )

        cmd = mock_run.call_args[0][0]
        # Each label gets its own --label flag
        label_indices = [i for i, c in enumerate(cmd) if c == "--label"]
        assert len(label_indices) == 2
        assert cmd[label_indices[0] + 1] == "DRC"
        assert cmd[label_indices[1] + 1] == "layout"

    def test_fetch_issues_with_state_filter(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="[]", stderr=""
            )
            source.fetch_issues(SourceConfig(repo="o/r", state="closed"))

        cmd = mock_run.call_args[0][0]
        state_idx = cmd.index("--state")
        assert cmd[state_idx + 1] == "closed"

    def test_fetch_issues_state_all_no_flag(self, source: GitHubSource):
        """state='all' should not pass --state flag (gh default)."""
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="[]", stderr=""
            )
            source.fetch_issues(SourceConfig(repo="o/r", state="all"))

        cmd = mock_run.call_args[0][0]
        assert "--state" not in cmd

    def test_fetch_issues_with_since(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="[]", stderr=""
            )
            source.fetch_issues(
                SourceConfig(repo="o/r", since="2025-06-01")
            )

        cmd = mock_run.call_args[0][0]
        search_idx = cmd.index("--search")
        assert "created:>=2025-06-01" in cmd[search_idx + 1]

    def test_fetch_issues_limit(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="[]", stderr=""
            )
            source.fetch_issues(SourceConfig(repo="o/r", limit=10))

        cmd = mock_run.call_args[0][0]
        limit_idx = cmd.index("--limit")
        assert cmd[limit_idx + 1] == "10"


class TestFetchSingleIssue:
    def test_fetch_single_issue(self, source: GitHubSource):
        issue = _make_issue(835, title="Abutment check")
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issue), stderr=""
            )
            result = source.fetch_single_issue("IHP-GmbH/IHP-Open-PDK", 835)

        assert result["number"] == 835
        cmd = mock_run.call_args[0][0]
        assert "view" in cmd
        assert "835" in cmd


# -- synthesize_issue tests --


class TestSynthesizeIssue:
    def test_synthesize_basic(self, source: GitHubSource):
        issue = _make_issue(42, title="Fix DRC rule", body="The rule is wrong.")
        md = source.synthesize_issue(issue, "owner/repo")

        assert "# GitHub Issue #42: Fix DRC rule" in md
        assert "**Repository**: owner/repo" in md
        assert "The rule is wrong." in md
        assert "## Description" in md
        assert "## Summary" in md

    def test_synthesize_with_comments(self, source: GitHubSource):
        comments = [
            _make_comment("alice", "This is the first comment with detail.", "MEMBER"),
            _make_comment("bob", "I agree, here is more context for this.", "CONTRIBUTOR"),
        ]
        issue = _make_issue(10, comments=comments)
        md = source.synthesize_issue(issue, "o/r")

        assert "## Key Discussion Points" in md
        assert "@alice" in md
        assert "@bob" in md

    def test_synthesize_closed_issue(self, source: GitHubSource):
        comments = [
            _make_comment("fixer", "Fixed in commit abc123, this resolves it.", "MEMBER"),
        ]
        issue = _make_issue(
            5, state="CLOSED", comments=comments,
            closed_at="2026-02-01T10:00:00Z",
        )
        md = source.synthesize_issue(issue, "o/r")

        assert "CLOSED" in md
        assert "Resolved" in md

    def test_synthesize_no_body(self, source: GitHubSource):
        issue = _make_issue(1, body="")
        md = source.synthesize_issue(issue, "o/r")
        assert "No description provided" in md

    def test_synthesize_labels(self, source: GitHubSource):
        issue = _make_issue(1, labels=["DRC", "layout", "P1"])
        md = source.synthesize_issue(issue, "o/r")
        assert "DRC" in md
        assert "layout" in md
        assert "P1" in md

    def test_synthesize_html_comments_stripped(self, source: GitHubSource):
        issue = _make_issue(1, body="Real text <!-- hidden --> more text")
        md = source.synthesize_issue(issue, "o/r")
        assert "<!-- hidden -->" not in md
        assert "Real text" in md
        assert "more text" in md

    def test_synthesize_author_association(self, source: GitHubSource):
        issue = _make_issue(1, author="admin", author_assoc="OWNER")
        md = source.synthesize_issue(issue, "o/r")
        assert "OWNER" in md


# -- Comment ranking tests --


class TestCommentRanking:
    def test_ranking_by_association(self, source: GitHubSource):
        comments = [
            _make_comment("nobody", "Normal comment with enough text here.", "NONE"),
            _make_comment("owner", "Owner comment with enough text here too.", "OWNER"),
            _make_comment("member", "Member comment with enough text for filter.", "MEMBER"),
        ]
        ranked = source._rank_comments(comments, max_comments=10)
        # Owner should rank first, then member, then nobody
        assert ranked[0].author == "owner"
        assert ranked[1].author == "member"
        assert ranked[2].author == "nobody"

    def test_ranking_by_reactions(self, source: GitHubSource):
        comments = [
            _make_comment("a", "Less popular but still enough text here.", "NONE",
                          reactions={"totalCount": 1}),
            _make_comment("b", "Very popular and has enough text in body.", "NONE",
                          reactions={"totalCount": 10}),
        ]
        ranked = source._rank_comments(comments, max_comments=10)
        assert ranked[0].author == "b"

    def test_skip_bots(self, source: GitHubSource):
        comments = [
            _make_comment("dependabot[bot]", "Bumped version to 1.2.3, updated deps."),
            _make_comment("human", "Real discussion comment with enough text."),
        ]
        ranked = source._rank_comments(comments, max_comments=10)
        assert len(ranked) == 1
        assert ranked[0].author == "human"

    def test_skip_short_comments(self, source: GitHubSource):
        comments = [
            _make_comment("a", "+1"),
            _make_comment("b", "LGTM"),
            _make_comment("c", "This has enough text to pass the filter easily."),
        ]
        ranked = source._rank_comments(comments, max_comments=10)
        assert len(ranked) == 1
        assert ranked[0].author == "c"

    def test_max_limit(self, source: GitHubSource):
        comments = [
            _make_comment(f"user{i}", f"Comment number {i} with enough text for filter.")
            for i in range(20)
        ]
        ranked = source._rank_comments(comments, max_comments=5)
        assert len(ranked) == 5

    def test_code_block_bonus(self, source: GitHubSource):
        comments = [
            _make_comment("plain", "Just a normal comment with enough text here.", "NONE"),
            _make_comment(
                "coder",
                "Here is a fix:\n```python\nprint('hello')\n```\nThat should work.",
                "NONE",
            ),
        ]
        ranked = source._rank_comments(comments, max_comments=10)
        assert ranked[0].author == "coder"


# -- detect_repo tests --


class TestDetectRepo:
    def test_detect_repo_ssh(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="origin\tgit@github.com:IHP-GmbH/IHP-Open-PDK.git (fetch)\n",
                stderr="",
            )
            result = source.detect_repo()
        assert result == "IHP-GmbH/IHP-Open-PDK"

    def test_detect_repo_https(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="origin\thttps://github.com/owner/repo.git (fetch)\n",
                stderr="",
            )
            result = source.detect_repo()
        assert result == "owner/repo"

    def test_detect_repo_https_no_git_suffix(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="origin\thttps://github.com/owner/repo (fetch)\n",
                stderr="",
            )
            result = source.detect_repo()
        assert result == "owner/repo"

    def test_detect_repo_none(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="origin\thttps://gitlab.com/owner/repo.git (fetch)\n",
                stderr="",
            )
            result = source.detect_repo()
        assert result is None

    def test_detect_repo_git_not_found(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError
            result = source.detect_repo()
        assert result is None


# -- Error handling tests --


class TestErrorHandling:
    def test_gh_not_installed(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError
            with pytest.raises(GitHubSourceError, match="gh CLI not found"):
                source.fetch_issues(SourceConfig(repo="o/r"))

    def test_gh_auth_error(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="To get started with GitHub CLI, please run: gh auth login",
            )
            with pytest.raises(GitHubSourceError, match="auth"):
                source.fetch_issues(SourceConfig(repo="o/r"))

    def test_gh_generic_error(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="some error"
            )
            with pytest.raises(GitHubSourceError, match="some error"):
                source.fetch_issues(SourceConfig(repo="o/r"))

    def test_gh_timeout(self, source: GitHubSource):
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=60)
            with pytest.raises(GitHubSourceError, match="timed out"):
                source.fetch_issues(SourceConfig(repo="o/r"))


# -- import_issues integration tests --


class TestImportIssues:
    def test_batch_import(self, source: GitHubSource):
        issues = [
            _make_issue(1, title="First"),
            _make_issue(2, title="Second"),
        ]
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issues), stderr=""
            )
            config = SourceConfig(repo="owner/repo")
            items = source.import_issues(config)

        assert len(items) == 2
        assert all(it.type == "knowledge" for it in items)
        assert items[0].key == "github-issue-owner-repo-1"
        assert items[1].key == "github-issue-owner-repo-2"

    def test_single_issue_import(self, source: GitHubSource):
        issue = _make_issue(835, title="Abutment check")
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issue), stderr=""
            )
            config = SourceConfig(repo="IHP-GmbH/IHP-Open-PDK", issue_number=835)
            items = source.import_issues(config)

        assert len(items) == 1
        assert items[0].key == "github-issue-ihp-gmbh-ihp-open-pdk-835"
        assert "Abutment check" in items[0].content

    def test_as_decisions(self, source: GitHubSource):
        comments = [
            _make_comment("fixer", "Fixed by adding guard ring, confirmed in testing.", "MEMBER"),
        ]
        issue = _make_issue(
            10, title="Guard ring requirement", state="CLOSED",
            body="Need guard rings for ESD.", comments=comments,
            closed_at="2026-02-01T00:00:00Z",
        )
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issue), stderr=""
            )
            config = SourceConfig(
                repo="owner/repo", issue_number=10, as_decisions=True
            )
            items = source.import_issues(config)

        # Should get both knowledge and decision
        assert len(items) == 2
        knowledge = [it for it in items if it.type == "knowledge"]
        decisions = [it for it in items if it.type == "decision"]
        assert len(knowledge) == 1
        assert len(decisions) == 1
        assert decisions[0].title == "Guard ring requirement"
        assert "guard ring" in decisions[0].decision_text.lower()

    def test_as_decisions_open_issue_no_decision(self, source: GitHubSource):
        """Open issues should not produce decision records even with --as-decisions."""
        issue = _make_issue(1, state="OPEN")
        with patch("ctx.sources.github.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issue), stderr=""
            )
            config = SourceConfig(
                repo="o/r", issue_number=1, as_decisions=True
            )
            items = source.import_issues(config)

        assert len(items) == 1
        assert items[0].type == "knowledge"


# -- Key generation tests --


class TestKeyGeneration:
    def test_key_basic(self):
        assert _repo_slug("owner/repo") == "owner-repo"

    def test_key_with_org(self):
        assert _repo_slug("IHP-GmbH/IHP-Open-PDK") == "ihp-gmbh-ihp-open-pdk"

    def test_key_sanitized(self):
        # sanitize_key lowercases and strips special chars
        slug = _repo_slug("My.Org/My_Repo")
        assert "/" not in slug
        assert "." not in slug


# -- Helper function tests --


class TestHelpers:
    def test_format_date(self):
        assert _format_date("2026-02-23T14:30:00Z") == "2026-02-23"
        assert _format_date("") == ""
        assert _format_date("2026-01-01") == "2026-01-01"

    def test_clean_body(self):
        assert _clean_body("text <!-- comment --> more") == "text  more"
        assert _clean_body("a\n\n\n\n\nb") == "a\n\nb"
        assert _clean_body("") == ""

    def test_parse_github_remote_ssh(self):
        output = "origin\tgit@github.com:IHP-GmbH/IHP-Open-PDK.git (fetch)\n"
        assert _parse_github_remote(output) == "IHP-GmbH/IHP-Open-PDK"

    def test_parse_github_remote_https(self):
        output = "origin\thttps://github.com/owner/repo.git (fetch)\n"
        assert _parse_github_remote(output) == "owner/repo"

    def test_parse_github_remote_no_match(self):
        output = "origin\thttps://gitlab.com/owner/repo.git (fetch)\n"
        assert _parse_github_remote(output) is None

    def test_parse_github_remote_multiple_remotes(self):
        output = (
            "origin\thttps://gitlab.com/other/thing.git (fetch)\n"
            "upstream\tgit@github.com:real/repo.git (fetch)\n"
        )
        assert _parse_github_remote(output) == "real/repo"
