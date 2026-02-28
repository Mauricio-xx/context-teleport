"""Pydantic v2 models for all context store types."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ctx.core.migrations import SCHEMA_VERSION

ACTIVITY_STALE_HOURS = 48


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# -- Manifest --


class AdapterConfig(BaseModel):
    enabled: bool = True


class TeamMember(BaseModel):
    name: str
    machine: str
    added: datetime = Field(default_factory=_now)


class ProjectInfo(BaseModel):
    name: str
    id: str = Field(default_factory=_uuid)
    repo_url: str = ""


class Manifest(BaseModel):
    schema_version: str = SCHEMA_VERSION
    project: ProjectInfo
    adapters: dict[str, AdapterConfig] = Field(
        default_factory=lambda: {"claude_code": AdapterConfig(enabled=True)}
    )
    team: dict[str, list[TeamMember]] = Field(default_factory=lambda: {"members": []})
    languages: list[str] = Field(default_factory=list)
    build_systems: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


# -- Knowledge --


class KnowledgeEntry(BaseModel):
    key: str
    content: str
    updated_at: datetime = Field(default_factory=_now)
    author: str = ""
    agent: str = ""


# -- Conventions --


class ConventionEntry(BaseModel):
    key: str
    content: str
    updated_at: datetime = Field(default_factory=_now)
    author: str = ""


# -- Skills --


class SkillEntry(BaseModel):
    name: str
    description: str
    content: str  # complete SKILL.md (frontmatter + body)
    updated_at: datetime = Field(default_factory=_now)
    agent: str = ""


# -- Decisions (ADR) --


class DecisionStatus(str, Enum):
    proposed = "proposed"
    accepted = "accepted"
    deprecated = "deprecated"
    superseded = "superseded"


class Decision(BaseModel):
    id: int
    title: str
    status: DecisionStatus = DecisionStatus.accepted
    date: datetime = Field(default_factory=_now)
    author: str = ""
    context: str = ""
    decision: str = ""
    consequences: str = ""

    @property
    def slug(self) -> str:
        return self.title.lower().replace(" ", "-").replace("/", "-")[:60]

    @property
    def filename(self) -> str:
        return f"{self.id:04d}-{self.slug}.md"

    def to_markdown(self) -> str:
        lines = [
            f"# {self.id:04d} - {self.title}",
            "",
            f"**Date**: {self.date.strftime('%Y-%m-%d')}",
            f"**Status**: {self.status.value}",
            f"**Author**: {self.author}",
            "",
            "## Context",
            self.context or "(no context provided)",
            "",
            "## Decision",
            self.decision or "(no decision recorded)",
            "",
            "## Consequences",
            self.consequences or "(no consequences noted)",
            "",
        ]
        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, text: str, decision_id: int | None = None) -> Decision:
        """Parse a decision from markdown. Best-effort extraction."""
        lines = text.strip().split("\n")
        title = ""
        status = DecisionStatus.accepted
        date = _now()
        author = ""
        sections: dict[str, list[str]] = {}
        current_section: str | None = None

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# ") and not title:
                # Parse "# 0001 - Title" or "# Title"
                header = stripped[2:].strip()
                if " - " in header:
                    parts = header.split(" - ", 1)
                    try:
                        decision_id = int(parts[0].strip())
                    except ValueError:
                        pass
                    title = parts[1].strip()
                else:
                    title = header
            elif stripped.startswith("**Date**:"):
                date_str = stripped.split(":", 1)[1].strip().rstrip("*")
                try:
                    date = datetime.strptime(date_str.strip(), "%Y-%m-%d").replace(
                        tzinfo=timezone.utc
                    )
                except ValueError:
                    pass
            elif stripped.startswith("**Status**:"):
                status_str = stripped.split(":", 1)[1].strip().rstrip("*")
                try:
                    status = DecisionStatus(status_str.strip())
                except ValueError:
                    pass
            elif stripped.startswith("**Author**:"):
                author = stripped.split(":", 1)[1].strip().rstrip("*")
            elif stripped.startswith("## "):
                current_section = stripped[3:].strip().lower()
                sections[current_section] = []
            elif current_section:
                sections.setdefault(current_section, []).append(line)

        return cls(
            id=decision_id or 0,
            title=title or "Untitled",
            status=status,
            date=date,
            author=author,
            context="\n".join(sections.get("context", [])).strip(),
            decision="\n".join(sections.get("decision", [])).strip(),
            consequences="\n".join(sections.get("consequences", [])).strip(),
        )


# -- Session state --


class ActivityEntry(BaseModel):
    member: str
    agent: str = ""
    machine: str = ""
    task: str = ""
    issue_ref: str = ""
    status: str = "active"  # "active" or "idle"
    updated_at: datetime = Field(default_factory=_now)


class ActiveState(BaseModel):
    current_task: str = ""
    blockers: list[str] = Field(default_factory=list)
    progress: dict[str, Any] = Field(default_factory=dict)
    last_agent: str = ""
    last_machine: str = ""
    updated_at: datetime = Field(default_factory=_now)


class RoadmapItem(BaseModel):
    title: str
    status: str = "planned"
    milestone: str = ""


class Roadmap(BaseModel):
    items: list[RoadmapItem] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=_now)


# -- Preferences --


class TeamPreferences(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class UserPreferences(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


# -- Session history --


class SessionSummary(BaseModel):
    id: str = Field(default_factory=_uuid)
    agent: str = ""
    user: str = ""
    machine: str = ""
    started: datetime = Field(default_factory=_now)
    ended: datetime | None = None
    summary: str = ""
    knowledge_added: list[str] = Field(default_factory=list)
    decisions_added: list[str] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)


# -- Skill tracking (Phase 7a) --


class SkillUsageEvent(BaseModel):
    id: str = Field(default_factory=_uuid)
    session_id: str = ""
    agent: str = ""
    timestamp: datetime = Field(default_factory=_now)


class SkillFeedback(BaseModel):
    id: str = Field(default_factory=_uuid)
    agent: str = ""
    rating: int = 3
    comment: str = ""
    timestamp: datetime = Field(default_factory=_now)


class SkillStats(BaseModel):
    """Read-only aggregated view, computed from ndjson files."""

    skill_name: str
    usage_count: int = 0
    avg_rating: float = 0.0
    rating_count: int = 0
    last_used: datetime | None = None
    needs_attention: bool = False


# -- Skill proposals (Phase 7b) --


class ProposalStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"
    upstream = "upstream"


class SkillProposal(BaseModel):
    id: str = Field(default_factory=_uuid)
    skill_name: str
    agent: str = ""
    rationale: str = ""
    proposed_content: str = ""
    diff_summary: str = ""
    status: ProposalStatus = ProposalStatus.pending
    created_at: datetime = Field(default_factory=_now)
    resolved_at: datetime | None = None
    resolved_by: str = ""
