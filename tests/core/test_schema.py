"""Tests for Pydantic schema models."""

from ctx.core.schema import (
    ActiveState,
    Decision,
    DecisionStatus,
    KnowledgeEntry,
    Manifest,
    ProjectInfo,
    SessionSummary,
)


class TestManifest:
    def test_create_default(self):
        m = Manifest(project=ProjectInfo(name="test"))
        assert m.schema_version == "0.1.0"
        assert m.project.name == "test"
        assert m.project.id  # UUID generated
        assert "claude_code" in m.adapters

    def test_serialization_roundtrip(self):
        m = Manifest(project=ProjectInfo(name="test"))
        json_str = m.model_dump_json()
        m2 = Manifest.model_validate_json(json_str)
        assert m2.project.name == "test"
        assert m2.schema_version == m.schema_version


class TestDecision:
    def test_slug_generation(self):
        d = Decision(id=1, title="Use PostgreSQL over SQLite")
        assert d.slug == "use-postgresql-over-sqlite"
        assert d.filename == "0001-use-postgresql-over-sqlite.md"

    def test_to_markdown(self):
        d = Decision(
            id=1,
            title="Use PostgreSQL",
            context="Need a database",
            decision="Use PostgreSQL",
            consequences="Managed DB required",
            author="dev1@machine",
        )
        md = d.to_markdown()
        assert "# 0001 - Use PostgreSQL" in md
        assert "## Context" in md
        assert "Need a database" in md
        assert "**Author**: dev1@machine" in md

    def test_from_markdown_roundtrip(self):
        d = Decision(
            id=5,
            title="Use Redis",
            status=DecisionStatus.accepted,
            context="Caching needed",
            decision="Redis for caching",
            consequences="More infra",
            author="dev@box",
        )
        md = d.to_markdown()
        parsed = Decision.from_markdown(md)
        assert parsed.id == 5
        assert parsed.title == "Use Redis"
        assert parsed.status == DecisionStatus.accepted
        assert "Caching needed" in parsed.context
        assert "Redis for caching" in parsed.decision

    def test_from_markdown_minimal(self):
        text = "# Some Decision\n\nJust some text."
        d = Decision.from_markdown(text)
        assert d.title == "Some Decision"


class TestKnowledgeEntry:
    def test_create(self):
        e = KnowledgeEntry(key="arch", content="Hexagonal")
        assert e.key == "arch"
        assert e.content == "Hexagonal"


class TestSessionSummary:
    def test_serialization(self):
        s = SessionSummary(
            agent="claude-code",
            user="dev1",
            summary="Implemented auth flow",
            knowledge_added=["known-issues"],
        )
        json_str = s.model_dump_json()
        s2 = SessionSummary.model_validate_json(json_str)
        assert s2.agent == "claude-code"
        assert s2.knowledge_added == ["known-issues"]


class TestActiveState:
    def test_defaults(self):
        s = ActiveState()
        assert s.current_task == ""
        assert s.blockers == []
        assert s.progress == {}
