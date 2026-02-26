"""Tests for skill improvement proposals (Phase 7b)."""

from __future__ import annotations

import pytest

from ctx.core.frontmatter import build_frontmatter
from ctx.core.schema import ProposalStatus, SkillProposal
from ctx.core.store import ContextStore, StoreError


@pytest.fixture
def store(tmp_path):
    s = ContextStore(tmp_path)
    s.init(project_name="test-proposals")
    return s


def _skill_content(name, body="# Instructions\n"):
    return build_frontmatter({"name": name, "description": f"Skill {name}"}, body)


@pytest.fixture
def store_with_skill(store):
    store.set_skill("debug-drc", _skill_content("debug-drc", "# Original\nOld content\n"))
    return store


class TestCreateSkillProposal:
    def test_create_proposal(self, store_with_skill):
        new_content = _skill_content("debug-drc", "# Improved\nNew content with fix\n")
        proposal = store_with_skill.create_skill_proposal(
            "debug-drc", new_content, rationale="Added false positive handling", agent="claude"
        )
        assert isinstance(proposal, SkillProposal)
        assert proposal.skill_name == "debug-drc"
        assert proposal.agent == "claude"
        assert proposal.status == ProposalStatus.pending
        assert proposal.diff_summary
        assert "+" in proposal.diff_summary
        assert proposal.rationale == "Added false positive handling"

    def test_proposal_persisted_to_disk(self, store_with_skill):
        new_content = _skill_content("debug-drc", "# v2\n")
        proposal = store_with_skill.create_skill_proposal("debug-drc", new_content)
        path = store_with_skill._skill_proposals_dir("debug-drc") / f"{proposal.id}.json"
        assert path.is_file()

    def test_proposal_nonexistent_skill(self, store):
        with pytest.raises(StoreError, match="not found"):
            store.create_skill_proposal("ghost", "content")

    def test_diff_summary_counts(self, store_with_skill):
        new_content = _skill_content("debug-drc", "# Improved\nLine A\nLine B\n")
        proposal = store_with_skill.create_skill_proposal("debug-drc", new_content)
        # Should contain +N/-M format
        assert "/" in proposal.diff_summary


class TestListSkillProposals:
    def test_empty(self, store_with_skill):
        assert store_with_skill.list_skill_proposals() == []

    def test_list_all(self, store_with_skill):
        c1 = _skill_content("debug-drc", "# v1\n")
        c2 = _skill_content("debug-drc", "# v2\n")
        store_with_skill.create_skill_proposal("debug-drc", c1)
        store_with_skill.create_skill_proposal("debug-drc", c2)
        assert len(store_with_skill.list_skill_proposals()) == 2

    def test_filter_by_skill(self, store):
        store.set_skill("a", _skill_content("a"))
        store.set_skill("b", _skill_content("b"))
        store.create_skill_proposal("a", _skill_content("a", "# new\n"))
        store.create_skill_proposal("b", _skill_content("b", "# new\n"))
        assert len(store.list_skill_proposals(skill_name="a")) == 1

    def test_filter_by_status(self, store_with_skill):
        c = _skill_content("debug-drc", "# new\n")
        p = store_with_skill.create_skill_proposal("debug-drc", c)
        store_with_skill.resolve_skill_proposal("debug-drc", p.id, accept=True)
        pending = store_with_skill.list_skill_proposals(status=ProposalStatus.pending)
        accepted = store_with_skill.list_skill_proposals(status=ProposalStatus.accepted)
        assert len(pending) == 0
        assert len(accepted) == 1


class TestGetSkillProposal:
    def test_get_existing(self, store_with_skill):
        c = _skill_content("debug-drc", "# v2\n")
        created = store_with_skill.create_skill_proposal("debug-drc", c)
        fetched = store_with_skill.get_skill_proposal("debug-drc", created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_nonexistent(self, store_with_skill):
        assert store_with_skill.get_skill_proposal("debug-drc", "bad-id") is None


class TestResolveSkillProposal:
    def test_accept_applies_content(self, store_with_skill):
        new_content = _skill_content("debug-drc", "# Improved content\n")
        p = store_with_skill.create_skill_proposal("debug-drc", new_content)
        result = store_with_skill.resolve_skill_proposal("debug-drc", p.id, accept=True, resolved_by="user")
        assert result.status == ProposalStatus.accepted
        assert result.resolved_by == "user"
        assert result.resolved_at is not None
        # Verify skill content was updated
        skill = store_with_skill.get_skill("debug-drc")
        assert "Improved content" in skill.content

    def test_reject_does_not_apply(self, store_with_skill):
        original = store_with_skill.get_skill("debug-drc").content
        new_content = _skill_content("debug-drc", "# Should not apply\n")
        p = store_with_skill.create_skill_proposal("debug-drc", new_content)
        result = store_with_skill.resolve_skill_proposal("debug-drc", p.id, accept=False)
        assert result.status == ProposalStatus.rejected
        skill = store_with_skill.get_skill("debug-drc")
        assert skill.content == original

    def test_resolve_nonexistent(self, store_with_skill):
        result = store_with_skill.resolve_skill_proposal("debug-drc", "bad-id", accept=True)
        assert result is None

    def test_resolve_updates_file(self, store_with_skill):
        c = _skill_content("debug-drc", "# v2\n")
        p = store_with_skill.create_skill_proposal("debug-drc", c)
        store_with_skill.resolve_skill_proposal("debug-drc", p.id, accept=True)
        # Re-read from disk
        fetched = store_with_skill.get_skill_proposal("debug-drc", p.id)
        assert fetched.status == ProposalStatus.accepted


class TestRmSkillCleansProposals:
    def test_rm_removes_proposals_dir(self, store_with_skill):
        c = _skill_content("debug-drc", "# v2\n")
        store_with_skill.create_skill_proposal("debug-drc", c)
        store_with_skill.rm_skill("debug-drc")
        assert not store_with_skill._skill_proposals_dir("debug-drc").exists()
