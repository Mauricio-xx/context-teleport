"""ContextStore: central component managing the .context-teleport/ directory."""

from __future__ import annotations

import re
from pathlib import Path

from ctx.core.schema import (
    ActiveState,
    Decision,
    DecisionStatus,
    KnowledgeEntry,
    Manifest,
    ProjectInfo,
    ProposalStatus,
    Roadmap,
    SessionSummary,
    SkillEntry,
    SkillFeedback,
    SkillProposal,
    SkillStats,
    SkillUsageEvent,
    TeamPreferences,
    UserPreferences,
)
from ctx.core.scope import Scope, ScopeMap
from ctx.utils.paths import STORE_DIR, get_author, sanitize_key


class StoreError(Exception):
    pass


class ContextStore:
    """Manages read/write operations on the .context-teleport/ directory."""

    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.store_dir = self.root / STORE_DIR

    @property
    def initialized(self) -> bool:
        return (self.store_dir / "manifest.json").is_file()

    # -- Initialization --

    def init(self, project_name: str | None = None, repo_url: str = "") -> Manifest:
        """Initialize a new context store."""
        if self.initialized:
            raise StoreError("Context store already initialized")

        name = project_name or self.root.name

        # Create directory structure
        dirs = [
            self.store_dir / "knowledge" / "decisions",
            self.store_dir / "skills",
            self.store_dir / "state",
            self.store_dir / "preferences",
            self.store_dir / "history",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Create manifest
        manifest = Manifest(
            project=ProjectInfo(name=name, repo_url=repo_url),
        )
        self._write_json(self.store_dir / "manifest.json", manifest)

        # Create scope sidecar files
        ScopeMap.ensure_exists(self.store_dir / "knowledge")
        ScopeMap.ensure_exists(self.store_dir / "knowledge" / "decisions")
        ScopeMap.ensure_exists(self.store_dir / "skills")

        # Create .gitignore for private files
        self._rebuild_gitignore()

        # Create empty state/roadmap.json
        self._write_json(self.store_dir / "state" / "roadmap.json", Roadmap())

        # Create empty preferences
        self._write_json(self.store_dir / "preferences" / "team.json", TeamPreferences())

        # Create empty history file
        (self.store_dir / "history" / "sessions.ndjson").touch()

        return manifest

    def _require_init(self) -> None:
        if not self.initialized:
            raise StoreError("Context store not initialized. Run `context-teleport init` first.")

    # -- Scope management --

    _GITIGNORE_BASE = ["state/active.json", "preferences/user.json", ".pending_conflicts.json"]

    def _knowledge_meta_path(self) -> Path:
        return self.knowledge_dir() / ".meta.json"

    def _read_knowledge_meta(self) -> dict[str, dict[str, str]]:
        path = self._knowledge_meta_path()
        if not path.is_file():
            return {}
        import json
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_knowledge_meta(self, data: dict[str, dict[str, str]]) -> None:
        import json
        self._knowledge_meta_path().write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n"
        )

    def _set_knowledge_author(self, filename: str, author: str) -> None:
        data = self._read_knowledge_meta()
        entry = data.setdefault(filename, {})
        entry["author"] = author
        self._write_knowledge_meta(data)

    def _get_knowledge_author(self, filename: str) -> str:
        data = self._read_knowledge_meta()
        entry = data.get(filename, {})
        return entry.get("author", "")

    def _knowledge_scope_map(self) -> ScopeMap:
        return ScopeMap(self.knowledge_dir())

    def _decisions_scope_map(self) -> ScopeMap:
        return ScopeMap(self.decisions_dir())

    def _rebuild_gitignore(self) -> None:
        """Regenerate .gitignore from base entries + non-public files."""
        lines = list(self._GITIGNORE_BASE)
        for fname in sorted(self._knowledge_scope_map().non_public_files()):
            lines.append(f"knowledge/{fname}")
        for fname in sorted(self._decisions_scope_map().non_public_files()):
            lines.append(f"knowledge/decisions/{fname}")
        for fname in sorted(self._skills_scope_map().non_public_files()):
            lines.append(f"skills/{fname}")
        gitignore = self.store_dir / ".gitignore"
        gitignore.write_text("\n".join(lines) + "\n")

    def get_knowledge_scope(self, key: str) -> Scope:
        """Return the scope for a knowledge entry."""
        safe_key = sanitize_key(key)
        return self._knowledge_scope_map().get(f"{safe_key}.md")

    def set_knowledge_scope(self, key: str, scope: Scope) -> bool:
        """Change scope for an existing knowledge entry. Returns False if not found."""
        self._require_init()
        safe_key = sanitize_key(key)
        path = self.knowledge_dir() / f"{safe_key}.md"
        if not path.is_file():
            return False
        self._knowledge_scope_map().set(f"{safe_key}.md", scope)
        self._rebuild_gitignore()
        return True

    def get_decision_scope(self, id_or_title: str) -> Scope | None:
        """Return the scope for a decision, or None if decision not found."""
        dec = self.get_decision(id_or_title)
        if dec is None:
            return None
        return self._decisions_scope_map().get(dec.filename)

    def set_decision_scope(self, id_or_title: str, scope: Scope) -> bool:
        """Change scope for an existing decision. Returns False if not found."""
        self._require_init()
        dec = self.get_decision(id_or_title)
        if dec is None:
            return False
        self._decisions_scope_map().set(dec.filename, scope)
        self._rebuild_gitignore()
        return True

    # -- Manifest --

    def read_manifest(self) -> Manifest:
        self._require_init()
        return Manifest.model_validate_json(
            (self.store_dir / "manifest.json").read_text()
        )

    def write_manifest(self, manifest: Manifest) -> None:
        self._require_init()
        from ctx.core.schema import _now

        manifest.updated_at = _now()
        self._write_json(self.store_dir / "manifest.json", manifest)

    # -- Knowledge --

    def knowledge_dir(self) -> Path:
        return self.store_dir / "knowledge"

    def list_knowledge(self, scope: Scope | None = None) -> list[KnowledgeEntry]:
        self._require_init()
        smap = self._knowledge_scope_map()
        entries = []
        kdir = self.knowledge_dir()
        for f in sorted(kdir.glob("*.md")):
            if scope is not None and smap.get(f.name) != scope:
                continue
            entries.append(
                KnowledgeEntry(
                    key=f.stem,
                    content=f.read_text(),
                    updated_at=_datetime_from_mtime(f),
                    author=self._get_knowledge_author(f.name),
                )
            )
        return entries

    def get_knowledge(self, key: str) -> KnowledgeEntry | None:
        self._require_init()
        safe_key = sanitize_key(key)
        path = self.knowledge_dir() / f"{safe_key}.md"
        if not path.is_file():
            return None
        return KnowledgeEntry(
            key=safe_key,
            content=path.read_text(),
            updated_at=_datetime_from_mtime(path),
            author=self._get_knowledge_author(f"{safe_key}.md"),
        )

    def set_knowledge(
        self, key: str, content: str, author: str = "", scope: Scope | None = None
    ) -> KnowledgeEntry:
        self._require_init()
        safe_key = sanitize_key(key)
        path = self.knowledge_dir() / f"{safe_key}.md"
        path.write_text(content)
        resolved_author = author or get_author()
        self._set_knowledge_author(f"{safe_key}.md", resolved_author)
        if scope is not None:
            self._knowledge_scope_map().set(f"{safe_key}.md", scope)
            self._rebuild_gitignore()
        return KnowledgeEntry(
            key=safe_key,
            content=content,
            author=resolved_author,
        )

    def rm_knowledge(self, key: str) -> bool:
        self._require_init()
        safe_key = sanitize_key(key)
        filename = f"{safe_key}.md"
        path = self.knowledge_dir() / filename
        if path.is_file():
            path.unlink()
            self._knowledge_scope_map().remove(filename)
            # Clean up metadata sidecar entry
            meta = self._read_knowledge_meta()
            if filename in meta:
                del meta[filename]
                self._write_knowledge_meta(meta)
            self._rebuild_gitignore()
            return True
        return False

    # -- Decisions --

    def decisions_dir(self) -> Path:
        return self.store_dir / "knowledge" / "decisions"

    def _next_decision_id(self) -> int:
        existing = list(self.decisions_dir().glob("*.md"))
        if not existing:
            return 1
        ids = []
        for f in existing:
            match = re.match(r"^(\d+)-", f.name)
            if match:
                ids.append(int(match.group(1)))
        return max(ids, default=0) + 1

    def list_decisions(self, scope: Scope | None = None) -> list[Decision]:
        self._require_init()
        smap = self._decisions_scope_map()
        decisions = []
        for f in sorted(self.decisions_dir().glob("*.md")):
            if scope is not None and smap.get(f.name) != scope:
                continue
            match = re.match(r"^(\d+)-", f.name)
            did = int(match.group(1)) if match else 0
            text = f.read_text()
            decisions.append(Decision.from_markdown(text, decision_id=did))
        return decisions

    def get_decision(self, id_or_title: str) -> Decision | None:
        self._require_init()
        # Try by numeric id
        try:
            target_id = int(id_or_title)
            for f in self.decisions_dir().glob("*.md"):
                match = re.match(r"^(\d+)-", f.name)
                if match and int(match.group(1)) == target_id:
                    return Decision.from_markdown(f.read_text(), decision_id=target_id)
        except ValueError:
            pass
        # Try by title slug match
        slug = sanitize_key(id_or_title)
        for f in self.decisions_dir().glob("*.md"):
            if slug in f.stem:
                match = re.match(r"^(\d+)-", f.name)
                did = int(match.group(1)) if match else 0
                return Decision.from_markdown(f.read_text(), decision_id=did)
        return None

    def add_decision(
        self,
        title: str,
        context: str = "",
        decision_text: str = "",
        consequences: str = "",
        status: DecisionStatus = DecisionStatus.accepted,
        author: str = "",
        scope: Scope | None = None,
    ) -> Decision:
        self._require_init()
        did = self._next_decision_id()
        dec = Decision(
            id=did,
            title=title,
            status=status,
            author=author or get_author(),
            context=context,
            decision=decision_text,
            consequences=consequences,
        )
        path = self.decisions_dir() / dec.filename
        path.write_text(dec.to_markdown())
        if scope is not None:
            self._decisions_scope_map().set(dec.filename, scope)
            self._rebuild_gitignore()
        return dec

    # -- Skills --

    def skills_dir(self) -> Path:
        return self.store_dir / "skills"

    def _skills_scope_map(self) -> ScopeMap:
        return ScopeMap(self.skills_dir())

    def _safe_skill_name(self, name: str) -> str:
        """Sanitize a skill name and verify it resolves inside skills_dir."""
        safe = sanitize_key(name)
        resolved = (self.skills_dir() / safe).resolve()
        if not str(resolved).startswith(str(self.skills_dir().resolve())):
            raise StoreError(f"Invalid skill name: {name}")
        return safe

    def list_skills(self, scope: Scope | None = None) -> list[SkillEntry]:
        self._require_init()
        from ctx.core.frontmatter import parse_frontmatter

        smap = self._skills_scope_map()
        sdir = self.skills_dir()
        entries = []
        if not sdir.is_dir():
            return entries
        for skill_md in sorted(sdir.glob("*/SKILL.md")):
            scope_key = f"{skill_md.parent.name}/SKILL.md"
            if scope is not None and smap.get(scope_key) != scope:
                continue
            content = skill_md.read_text()
            meta, _body = parse_frontmatter(content)
            entries.append(
                SkillEntry(
                    name=meta.get("name", skill_md.parent.name),
                    description=meta.get("description", ""),
                    content=content,
                    updated_at=_datetime_from_mtime(skill_md),
                )
            )
        return entries

    def get_skill(self, name: str) -> SkillEntry | None:
        self._require_init()
        from ctx.core.frontmatter import parse_frontmatter

        name = self._safe_skill_name(name)
        path = self.skills_dir() / name / "SKILL.md"
        if not path.is_file():
            return None
        content = path.read_text()
        meta, _body = parse_frontmatter(content)
        return SkillEntry(
            name=meta.get("name", name),
            description=meta.get("description", ""),
            content=content,
            updated_at=_datetime_from_mtime(path),
        )

    def set_skill(
        self, name: str, content: str, agent: str = "", scope: Scope | None = None
    ) -> SkillEntry:
        self._require_init()
        from ctx.core.frontmatter import parse_frontmatter

        name = self._safe_skill_name(name)
        skill_dir = self.skills_dir() / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        path = skill_dir / "SKILL.md"
        path.write_text(content)
        meta, _body = parse_frontmatter(content)
        if scope is not None:
            self._skills_scope_map().set(f"{name}/SKILL.md", scope)
            self._rebuild_gitignore()
        return SkillEntry(
            name=meta.get("name", name),
            description=meta.get("description", ""),
            content=content,
            agent=agent,
        )

    def rm_skill(self, name: str) -> bool:
        self._require_init()
        import shutil as _shutil

        name = self._safe_skill_name(name)
        skill_dir = self.skills_dir() / name
        if skill_dir.is_dir():
            _shutil.rmtree(skill_dir)
            scope_key = f"{name}/SKILL.md"
            self._skills_scope_map().remove(scope_key)
            self._rebuild_gitignore()
            return True
        return False

    def get_skill_scope(self, name: str) -> Scope:
        name = self._safe_skill_name(name)
        return self._skills_scope_map().get(f"{name}/SKILL.md")

    def set_skill_scope(self, name: str, scope: Scope) -> bool:
        self._require_init()
        name = self._safe_skill_name(name)
        path = self.skills_dir() / name / "SKILL.md"
        if not path.is_file():
            return False
        self._skills_scope_map().set(f"{name}/SKILL.md", scope)
        self._rebuild_gitignore()
        return True

    # -- Skill tracking (Phase 7a) --

    def _skill_usage_path(self, name: str) -> Path:
        name = self._safe_skill_name(name)
        return self.skills_dir() / name / ".usage.ndjson"

    def _skill_feedback_path(self, name: str) -> Path:
        name = self._safe_skill_name(name)
        return self.skills_dir() / name / ".feedback.ndjson"

    def _skill_proposals_dir(self, name: str) -> Path:
        name = self._safe_skill_name(name)
        return self.skills_dir() / name / ".proposals"

    def record_skill_usage(
        self, skill_name: str, agent: str = "", session_id: str = ""
    ) -> SkillUsageEvent:
        """Append a usage event for a skill. Skill must exist."""
        self._require_init()
        skill_name = self._safe_skill_name(skill_name)
        if not (self.skills_dir() / skill_name / "SKILL.md").is_file():
            raise StoreError(f"Skill '{skill_name}' not found")
        event = SkillUsageEvent(agent=agent, session_id=session_id)
        path = self._skill_usage_path(skill_name)
        with open(path, "a") as f:
            f.write(event.model_dump_json() + "\n")
        return event

    def add_skill_feedback(
        self, skill_name: str, rating: int, comment: str = "", agent: str = ""
    ) -> SkillFeedback:
        """Add feedback for a skill. Rating must be 1-5."""
        self._require_init()
        skill_name = self._safe_skill_name(skill_name)
        if not (self.skills_dir() / skill_name / "SKILL.md").is_file():
            raise StoreError(f"Skill '{skill_name}' not found")
        if not 1 <= rating <= 5:
            raise StoreError(f"Rating must be 1-5, got {rating}")
        fb = SkillFeedback(agent=agent, rating=rating, comment=comment)
        path = self._skill_feedback_path(skill_name)
        with open(path, "a") as f:
            f.write(fb.model_dump_json() + "\n")
        return fb

    def list_skill_feedback(self, skill_name: str) -> list[SkillFeedback]:
        """Return all feedback entries for a skill."""
        self._require_init()
        skill_name = self._safe_skill_name(skill_name)
        path = self._skill_feedback_path(skill_name)
        if not path.is_file():
            return []
        entries = []
        for line in path.read_text().strip().split("\n"):
            if line.strip():
                entries.append(SkillFeedback.model_validate_json(line))
        return entries

    def _read_usage_events(self, skill_name: str) -> list[SkillUsageEvent]:
        skill_name = self._safe_skill_name(skill_name)
        path = self._skill_usage_path(skill_name)
        if not path.is_file():
            return []
        events = []
        for line in path.read_text().strip().split("\n"):
            if line.strip():
                events.append(SkillUsageEvent.model_validate_json(line))
        return events

    def get_skill_stats(self, skill_name: str) -> SkillStats:
        """Compute aggregated stats for a skill from its sidecar files."""
        self._require_init()
        skill_name = self._safe_skill_name(skill_name)
        usage = self._read_usage_events(skill_name)
        feedback = self.list_skill_feedback(skill_name)

        last_used = max((e.timestamp for e in usage), default=None) if usage else None
        avg = 0.0
        if feedback:
            avg = sum(f.rating for f in feedback) / len(feedback)
        needs_attention = avg < 3.0 and len(feedback) >= 2

        return SkillStats(
            skill_name=skill_name,
            usage_count=len(usage),
            avg_rating=round(avg, 2),
            rating_count=len(feedback),
            last_used=last_used,
            needs_attention=needs_attention,
        )

    def list_skill_stats(self) -> list[SkillStats]:
        """Return stats for all skills."""
        self._require_init()
        result = []
        sdir = self.skills_dir()
        if not sdir.is_dir():
            return result
        for skill_md in sorted(sdir.glob("*/SKILL.md")):
            name = skill_md.parent.name
            result.append(self.get_skill_stats(name))
        return result

    # -- Skill proposals (Phase 7b) --

    def create_skill_proposal(
        self,
        skill_name: str,
        proposed_content: str,
        rationale: str = "",
        agent: str = "",
    ) -> SkillProposal:
        """Create a proposal to improve a skill. Skill must exist."""
        import difflib

        self._require_init()
        skill_name = self._safe_skill_name(skill_name)
        skill = self.get_skill(skill_name)
        if skill is None:
            raise StoreError(f"Skill '{skill_name}' not found")

        # Compute diff summary
        old_lines = skill.content.splitlines()
        new_lines = proposed_content.splitlines()
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
        added = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
        removed = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))
        diff_summary = f"+{added}/-{removed} lines"

        proposal = SkillProposal(
            skill_name=skill_name,
            agent=agent,
            rationale=rationale,
            proposed_content=proposed_content,
            diff_summary=diff_summary,
        )

        pdir = self._skill_proposals_dir(skill_name)
        pdir.mkdir(parents=True, exist_ok=True)
        import json

        (pdir / f"{proposal.id}.json").write_text(
            json.dumps(proposal.model_dump(), indent=2, default=str) + "\n"
        )
        return proposal

    def list_skill_proposals(
        self,
        skill_name: str | None = None,
        status: ProposalStatus | None = None,
    ) -> list[SkillProposal]:
        """List proposals, optionally filtered by skill and/or status."""
        self._require_init()
        import json

        proposals: list[SkillProposal] = []
        sdir = self.skills_dir()
        if not sdir.is_dir():
            return proposals

        if skill_name:
            skill_name = self._safe_skill_name(skill_name)
        dirs = (
            [sdir / skill_name / ".proposals"]
            if skill_name
            else list(sdir.glob("*/.proposals"))
        )
        for pdir in dirs:
            if not pdir.is_dir():
                continue
            for f in sorted(pdir.glob("*.json")):
                data = json.loads(f.read_text())
                p = SkillProposal.model_validate(data)
                if status is not None and p.status != status:
                    continue
                proposals.append(p)
        return proposals

    def get_skill_proposal(
        self, skill_name: str, proposal_id: str
    ) -> SkillProposal | None:
        """Get a specific proposal by skill name and proposal ID."""
        self._require_init()
        import json

        skill_name = self._safe_skill_name(skill_name)
        path = self._skill_proposals_dir(skill_name) / f"{proposal_id}.json"
        if not path.is_file():
            return None
        data = json.loads(path.read_text())
        return SkillProposal.model_validate(data)

    def resolve_skill_proposal(
        self,
        skill_name: str,
        proposal_id: str,
        accept: bool,
        resolved_by: str = "",
    ) -> SkillProposal | None:
        """Accept or reject a proposal. If accepted, applies the content."""
        import json
        from ctx.core.schema import _now

        self._require_init()
        skill_name = self._safe_skill_name(skill_name)
        proposal = self.get_skill_proposal(skill_name, proposal_id)
        if proposal is None:
            return None

        proposal.status = ProposalStatus.accepted if accept else ProposalStatus.rejected
        proposal.resolved_at = _now()
        proposal.resolved_by = resolved_by

        if accept:
            self.set_skill(skill_name, proposal.proposed_content)

        path = self._skill_proposals_dir(skill_name) / f"{proposal_id}.json"
        path.write_text(
            json.dumps(proposal.model_dump(), indent=2, default=str) + "\n"
        )
        return proposal

    # -- Ephemeral cleanup --

    def clear_ephemeral(self) -> dict[str, int]:
        """Remove all entries with ephemeral scope. Returns counts of removed entries."""
        import shutil as _shutil

        self._require_init()
        removed = {"knowledge": 0, "decisions": 0, "skills": 0}

        # Knowledge
        for fname in self._knowledge_scope_map().list_by_scope(Scope.ephemeral):
            path = self.knowledge_dir() / fname
            if path.is_file():
                path.unlink()
                self._knowledge_scope_map().remove(fname)
                # Clean up metadata sidecar entry
                meta = self._read_knowledge_meta()
                if fname in meta:
                    del meta[fname]
                    self._write_knowledge_meta(meta)
                removed["knowledge"] += 1

        # Decisions
        for fname in self._decisions_scope_map().list_by_scope(Scope.ephemeral):
            path = self.decisions_dir() / fname
            if path.is_file():
                path.unlink()
                self._decisions_scope_map().remove(fname)
                removed["decisions"] += 1

        # Skills
        for fname in self._skills_scope_map().list_by_scope(Scope.ephemeral):
            # fname is like "skill-name/SKILL.md"
            skill_name = fname.split("/")[0]
            skill_dir = self.skills_dir() / skill_name
            if skill_dir.is_dir():
                _shutil.rmtree(skill_dir)
                self._skills_scope_map().remove(fname)
                removed["skills"] += 1

        self._rebuild_gitignore()
        return removed

    # -- State --

    def read_active_state(self) -> ActiveState:
        self._require_init()
        path = self.store_dir / "state" / "active.json"
        if path.is_file():
            return ActiveState.model_validate_json(path.read_text())
        return ActiveState()

    def write_active_state(self, state: ActiveState) -> None:
        self._require_init()
        from ctx.core.schema import _now

        state.updated_at = _now()
        self._write_json(self.store_dir / "state" / "active.json", state)

    def read_roadmap(self) -> Roadmap:
        self._require_init()
        path = self.store_dir / "state" / "roadmap.json"
        if path.is_file():
            return Roadmap.model_validate_json(path.read_text())
        return Roadmap()

    def write_roadmap(self, roadmap: Roadmap) -> None:
        self._require_init()
        self._write_json(self.store_dir / "state" / "roadmap.json", roadmap)

    # -- Preferences --

    def read_team_preferences(self) -> TeamPreferences:
        self._require_init()
        path = self.store_dir / "preferences" / "team.json"
        if path.is_file():
            return TeamPreferences.model_validate_json(path.read_text())
        return TeamPreferences()

    def write_team_preferences(self, prefs: TeamPreferences) -> None:
        self._require_init()
        self._write_json(self.store_dir / "preferences" / "team.json", prefs)

    def read_user_preferences(self) -> UserPreferences:
        self._require_init()
        path = self.store_dir / "preferences" / "user.json"
        if path.is_file():
            return UserPreferences.model_validate_json(path.read_text())
        return UserPreferences()

    def write_user_preferences(self, prefs: UserPreferences) -> None:
        self._require_init()
        self._write_json(self.store_dir / "preferences" / "user.json", prefs)

    # -- History --

    def append_session(self, session: SessionSummary) -> None:
        self._require_init()
        path = self.store_dir / "history" / "sessions.ndjson"
        with open(path, "a") as f:
            f.write(session.model_dump_json() + "\n")

    def list_sessions(self, limit: int = 50) -> list[SessionSummary]:
        self._require_init()
        path = self.store_dir / "history" / "sessions.ndjson"
        if not path.is_file():
            return []
        lines = path.read_text().strip().split("\n")
        lines = [line for line in lines if line.strip()]
        sessions = [SessionSummary.model_validate_json(line) for line in lines[-limit:]]
        return sessions

    # -- Utilities --

    def _write_json(self, path: Path, model) -> None:
        path.write_text(model.model_dump_json(indent=2) + "\n")

    def all_markdown_files(self) -> list[Path]:
        """Return all markdown files in the store."""
        return sorted(self.store_dir.rglob("*.md"))

    def summary(self) -> dict:
        """Generate a summary of the store contents."""
        self._require_init()
        manifest = self.read_manifest()
        knowledge = self.list_knowledge()
        decisions = self.list_decisions()
        skills = self.list_skills()
        state = self.read_active_state()
        sessions = self.list_sessions(limit=5)

        return {
            "project": manifest.project.name,
            "schema_version": manifest.schema_version,
            "knowledge_count": len(knowledge),
            "knowledge_keys": [k.key for k in knowledge],
            "decision_count": len(decisions),
            "decisions": [
                {"id": d.id, "title": d.title, "status": d.status.value} for d in decisions
            ],
            "skill_count": len(skills),
            "skill_names": [s.name for s in skills],
            "current_task": state.current_task,
            "blockers": state.blockers,
            "recent_sessions": len(sessions),
        }


def _datetime_from_mtime(path: Path):
    """Get a datetime from a file's mtime."""
    from datetime import datetime, timezone

    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
