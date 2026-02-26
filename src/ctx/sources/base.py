"""Base data structures for remote source importers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceConfig:
    """Configuration for a remote source import operation."""

    repo: str  # "owner/repo" (required)
    labels: list[str] = field(default_factory=list)  # filter by labels
    state: str = "all"  # "open", "closed", "all"
    since: str = ""  # ISO date filter
    issue_number: int | None = None  # single issue import
    limit: int = 50  # max issues to fetch
    as_decisions: bool = False  # import closed issues as decisions


@dataclass
class SourceItem:
    """A single item produced by a remote source importer.

    Can represent either a knowledge entry or a decision record.
    """

    type: str  # "knowledge" or "decision"
    key: str  # e.g. "github-issue-ihp-open-pdk-835"
    content: str  # synthesized markdown
    source: str  # origin URL or reference

    # Decision-specific fields (populated only when type == "decision")
    title: str = ""
    context: str = ""
    decision_text: str = ""
    consequences: str = ""
