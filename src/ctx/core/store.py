"""ContextStore: central component managing the .context-teleport/ directory."""

from __future__ import annotations

import json
import re
from pathlib import Path

from ctx.core.schema import (
    ActiveState,
    Decision,
    DecisionStatus,
    KnowledgeEntry,
    Manifest,
    ProjectInfo,
    Roadmap,
    SessionSummary,
    TeamPreferences,
    UserPreferences,
)
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

        # Create .gitignore for private files
        gitignore = self.store_dir / ".gitignore"
        gitignore.write_text("state/active.json\npreferences/user.json\n")

        # Create empty state/roadmap.json
        self._write_json(self.store_dir / "state" / "roadmap.json", Roadmap())

        # Create empty preferences
        self._write_json(self.store_dir / "preferences" / "team.json", TeamPreferences())

        # Create empty history file
        (self.store_dir / "history" / "sessions.ndjson").touch()

        return manifest

    def _require_init(self) -> None:
        if not self.initialized:
            raise StoreError("Context store not initialized. Run `ctx init` first.")

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

    def list_knowledge(self) -> list[KnowledgeEntry]:
        self._require_init()
        entries = []
        kdir = self.knowledge_dir()
        for f in sorted(kdir.glob("*.md")):
            entries.append(
                KnowledgeEntry(
                    key=f.stem,
                    content=f.read_text(),
                    updated_at=_datetime_from_mtime(f),
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
        )

    def set_knowledge(self, key: str, content: str, author: str = "") -> KnowledgeEntry:
        self._require_init()
        safe_key = sanitize_key(key)
        path = self.knowledge_dir() / f"{safe_key}.md"
        path.write_text(content)
        return KnowledgeEntry(
            key=safe_key,
            content=content,
            author=author or get_author(),
        )

    def rm_knowledge(self, key: str) -> bool:
        self._require_init()
        safe_key = sanitize_key(key)
        path = self.knowledge_dir() / f"{safe_key}.md"
        if path.is_file():
            path.unlink()
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

    def list_decisions(self) -> list[Decision]:
        self._require_init()
        decisions = []
        for f in sorted(self.decisions_dir().glob("*.md")):
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
        return dec

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
        lines = [l for l in lines if l.strip()]
        sessions = [SessionSummary.model_validate_json(l) for l in lines[-limit:]]
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
            "current_task": state.current_task,
            "blockers": state.blockers,
            "recent_sessions": len(sessions),
        }


def _datetime_from_mtime(path: Path):
    """Get a datetime from a file's mtime."""
    from datetime import datetime, timezone

    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
