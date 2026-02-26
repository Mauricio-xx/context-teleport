"""GitHub issue importer via gh CLI.

Fetches issues from GitHub repositories using the `gh` CLI tool,
synthesizes threaded discussions into structured knowledge entries,
and optionally records closed issues as decision records.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass

from ctx.sources.base import SourceConfig, SourceItem
from ctx.utils.paths import sanitize_key

# gh JSON fields we request for issue listing and single-issue view
_ISSUE_FIELDS = (
    "number,title,state,body,author,labels,createdAt,closedAt,comments,url,"
    "authorAssociation"
)

# Author association priority (higher = more relevant)
_ASSOCIATION_RANK: dict[str, int] = {
    "OWNER": 5,
    "MEMBER": 4,
    "CONTRIBUTOR": 3,
    "COLLABORATOR": 2,
    "NONE": 0,
}

# Minimum comment length to include (skip trivial reactions/thumbs-up text)
_MIN_COMMENT_LENGTH = 20

# Default max comments to include per issue
_DEFAULT_MAX_COMMENTS = 10


class GitHubSourceError(Exception):
    """Raised when a GitHub source operation fails."""


@dataclass
class _RankedComment:
    """Internal: a comment with its computed relevance score."""

    body: str
    author: str
    association: str
    created_at: str
    score: float


class GitHubSource:
    """Import GitHub issues as knowledge entries and decisions."""

    def import_issues(self, config: SourceConfig) -> list[SourceItem]:
        """Fetch and synthesize issues based on config.

        Returns a list of SourceItems ready to be written to the store.
        """
        if config.issue_number is not None:
            issue = self.fetch_single_issue(config.repo, config.issue_number)
            return self._synthesize_one(issue, config)

        issues = self.fetch_issues(config)
        items: list[SourceItem] = []
        for issue in issues:
            items.extend(self._synthesize_one(issue, config))
        return items

    def fetch_issues(self, config: SourceConfig) -> list[dict]:
        """Fetch issues from GitHub via gh CLI."""
        cmd = [
            "gh", "issue", "list",
            "--repo", config.repo,
            "--json", _ISSUE_FIELDS,
            "--limit", str(config.limit),
        ]

        if config.state != "all":
            cmd.extend(["--state", config.state])

        for label in config.labels:
            cmd.extend(["--label", label])

        if config.since:
            # gh uses --search for date filters with GitHub search syntax
            cmd.extend(["--search", f"created:>={config.since}"])

        return self._run_gh(cmd)

    def fetch_single_issue(self, repo: str, number: int) -> dict:
        """Fetch a single issue by number."""
        cmd = [
            "gh", "issue", "view", str(number),
            "--repo", repo,
            "--json", _ISSUE_FIELDS,
        ]
        return self._run_gh_single(cmd)

    def synthesize_issue(
        self, issue: dict, repo: str, max_comments: int = _DEFAULT_MAX_COMMENTS
    ) -> str:
        """Convert an issue dict into a structured markdown knowledge entry."""
        number = issue.get("number", "?")
        title = issue.get("title", "Untitled")
        state = issue.get("state", "unknown").upper()
        created = _format_date(issue.get("createdAt", ""))
        closed = _format_date(issue.get("closedAt", ""))
        author = _get_author_login(issue)
        author_assoc = issue.get("authorAssociation", "")
        labels = [lbl.get("name", "") for lbl in issue.get("labels", []) if lbl.get("name")]
        url = issue.get("url", f"https://github.com/{repo}/issues/{number}")
        body = _clean_body(issue.get("body", "") or "")

        lines = [
            f"# GitHub Issue #{number}: {title}",
            "",
            f"**Repository**: {repo}",
        ]

        meta_parts = [f"**State**: {state}"]
        if created:
            meta_parts.append(f"**Created**: {created}")
        if closed:
            meta_parts.append(f"**Closed**: {closed}")
        if author:
            author_str = f"**Author**: {author}"
            if author_assoc and author_assoc != "NONE":
                author_str += f" ({author_assoc})"
            meta_parts.append(author_str)
        lines.append(" | ".join(meta_parts))

        if labels:
            lines.append(f"**Labels**: {', '.join(labels)}")
        lines.append(f"**URL**: {url}")
        lines.append("")

        # Description
        lines.append("## Description")
        lines.append("")
        if body:
            lines.append(body)
        else:
            lines.append("*No description provided.*")
        lines.append("")

        # Comments
        comments = issue.get("comments", []) or []
        ranked = self._rank_comments(comments, max_comments)
        if ranked:
            lines.append("## Key Discussion Points")
            lines.append("")
            for c in ranked:
                assoc_tag = f" ({c.association})" if c.association and c.association != "NONE" else ""
                date_str = _format_date(c.created_at)
                date_tag = f" -- {date_str}" if date_str else ""
                lines.append(f"### @{c.author}{assoc_tag}{date_tag}")
                lines.append("")
                lines.append(_clean_body(c.body))
                lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        if state == "CLOSED":
            # Try to use the last substantive comment as resolution
            if ranked:
                lines.append(f"Resolved. Last comment by @{ranked[-1].author}.")
            else:
                lines.append("Issue closed.")
        else:
            lines.append("Issue is open.")
        lines.append("")

        return "\n".join(lines)

    def detect_repo(self) -> str | None:
        """Try to detect owner/repo from git remote origin."""
        try:
            result = subprocess.run(
                ["git", "remote", "-v"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                return None
            return _parse_github_remote(result.stdout)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    # -- Internal helpers --

    def _synthesize_one(self, issue: dict, config: SourceConfig) -> list[SourceItem]:
        """Synthesize a single issue into one or two SourceItems."""
        items: list[SourceItem] = []
        repo_slug = _repo_slug(config.repo)
        number = issue.get("number", 0)
        key = f"github-issue-{repo_slug}-{number}"
        content = self.synthesize_issue(issue, config.repo)
        url = issue.get("url", f"https://github.com/{config.repo}/issues/{number}")

        items.append(SourceItem(
            type="knowledge",
            key=key,
            content=content,
            source=url,
        ))

        # Optionally create a decision record for closed issues
        state = (issue.get("state", "") or "").upper()
        if config.as_decisions and state == "CLOSED":
            title = issue.get("title", "Untitled")
            body = _clean_body(issue.get("body", "") or "")
            context_text = body[:500] if body else "See linked GitHub issue."

            # Use last comment as decision text
            comments = issue.get("comments", []) or []
            ranked = self._rank_comments(comments, _DEFAULT_MAX_COMMENTS)
            if ranked:
                decision_text = _clean_body(ranked[-1].body)
            else:
                decision_text = "Resolved (no closing comment captured)."

            labels = [lbl.get("name", "") for lbl in issue.get("labels", []) if lbl.get("name")]
            consequences = f"Labels: {', '.join(labels)}" if labels else ""

            items.append(SourceItem(
                type="decision",
                key=key,  # not used for decisions (auto-numbered), but kept for reference
                content=content,
                source=url,
                title=title,
                context=context_text,
                decision_text=decision_text,
                consequences=consequences,
            ))

        return items

    def _rank_comments(
        self, comments: list[dict], max_comments: int
    ) -> list[_RankedComment]:
        """Rank and filter comments by relevance."""
        ranked: list[_RankedComment] = []

        for i, c in enumerate(comments):
            author = _get_author_login(c)
            body = (c.get("body", "") or "").strip()

            # Skip bots
            if "[bot]" in author:
                continue

            # Skip very short comments
            if len(body) < _MIN_COMMENT_LENGTH:
                continue

            association = c.get("authorAssociation", "NONE") or "NONE"
            created_at = c.get("createdAt", "")

            score = _ASSOCIATION_RANK.get(association, 0) * 10.0

            # Reaction bonus
            reactions = c.get("reactions", {})
            if isinstance(reactions, dict):
                total_reactions = reactions.get("totalCount", 0)
            elif isinstance(reactions, list):
                total_reactions = len(reactions)
            else:
                total_reactions = 0
            score += total_reactions * 2.0

            # Content signal bonus
            if "```" in body:
                score += 3.0
            if re.search(r"[\w/]+\.\w{1,5}", body):  # file path pattern
                score += 1.0

            # Position bonus: first and last comments
            if i == 0:
                score += 2.0
            if i == len(comments) - 1:
                score += 2.0

            ranked.append(_RankedComment(
                body=body,
                author=author,
                association=association,
                created_at=created_at,
                score=score,
            ))

        # Sort by score descending, then by position (preserve order for ties)
        ranked.sort(key=lambda c: c.score, reverse=True)
        return ranked[:max_comments]

    def _run_gh(self, cmd: list[str]) -> list[dict]:
        """Run a gh command that returns a JSON array."""
        raw = self._exec_gh(cmd)
        data = json.loads(raw)
        if not isinstance(data, list):
            return [data] if data else []
        return data

    def _run_gh_single(self, cmd: list[str]) -> dict:
        """Run a gh command that returns a single JSON object."""
        raw = self._exec_gh(cmd)
        data = json.loads(raw)
        if isinstance(data, list):
            if not data:
                raise GitHubSourceError("Issue not found")
            return data[0]
        return data

    def _exec_gh(self, cmd: list[str]) -> str:
        """Execute a gh CLI command and return stdout."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60,
            )
        except FileNotFoundError:
            raise GitHubSourceError(
                "gh CLI not found. Install it: https://cli.github.com/"
            )
        except subprocess.TimeoutExpired:
            raise GitHubSourceError("gh command timed out after 60 seconds")

        if result.returncode != 0:
            stderr = result.stderr.strip()
            if "auth login" in stderr or "not logged" in stderr.lower():
                raise GitHubSourceError(
                    f"gh authentication required. Run: gh auth login\n{stderr}"
                )
            raise GitHubSourceError(f"gh command failed: {stderr}")

        return result.stdout


# -- Module-level helpers --


def _repo_slug(repo: str) -> str:
    """Convert 'owner/repo' to 'owner-repo' for use in keys."""
    return sanitize_key(repo.replace("/", "-"))


def _get_author_login(obj: dict) -> str:
    """Extract author login from issue or comment dict."""
    author = obj.get("author", {})
    if isinstance(author, dict):
        return author.get("login", "unknown")
    if isinstance(author, str):
        return author
    return "unknown"


def _format_date(iso_date: str) -> str:
    """Format an ISO date string to YYYY-MM-DD."""
    if not iso_date:
        return ""
    # gh returns dates like "2026-02-23T14:30:00Z"
    return iso_date[:10]


def _clean_body(text: str) -> str:
    """Clean up issue/comment body text."""
    if not text:
        return ""
    # Strip HTML comments
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Collapse triple+ newlines to double
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_github_remote(remote_output: str) -> str | None:
    """Parse git remote -v output for a GitHub repository.

    Handles both SSH and HTTPS formats:
      git@github.com:owner/repo.git
      https://github.com/owner/repo.git
      https://github.com/owner/repo
    """
    for line in remote_output.splitlines():
        # SSH format
        m = re.search(r"github\.com[:/]([^/]+/[^/\s]+?)(?:\.git)?\s", line)
        if m:
            return m.group(1)
    return None
