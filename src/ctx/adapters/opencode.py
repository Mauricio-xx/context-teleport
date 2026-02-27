"""OpenCode adapter: import/export from AGENTS.md, SQLite sessions, MCP registration."""

from __future__ import annotations

import shutil
from pathlib import Path

from ctx.adapters._agents_md import parse_agents_md, write_agents_md_section
from ctx.adapters._mcp_reg import register_mcp_json, unregister_mcp_json
from ctx.core.scope import Scope
from ctx.core.store import ContextStore
from ctx.utils.paths import get_author


class OpenCodeAdapter:
    name = "opencode"

    def __init__(self, store: ContextStore) -> None:
        self.store = store

    def detect(self) -> bool:
        """Check for opencode binary and/or .opencode/ directory."""
        if shutil.which("opencode") is not None:
            return True
        if (self.store.root / ".opencode").is_dir():
            return True
        if (self.store.root / "opencode.json").is_file():
            return True
        return False

    def import_context(self, dry_run: bool = False) -> dict:
        """Import from OpenCode native formats."""
        items: list[dict] = []

        # 1. AGENTS.md
        agents_md = self.store.root / "AGENTS.md"
        if agents_md.is_file():
            entries = parse_agents_md(agents_md.read_text())
            for key, content in entries:
                items.append({
                    "type": "knowledge",
                    "key": key,
                    "source": "AGENTS.md",
                    "content": content,
                })

        # 2. SQLite sessions (read-only)
        db_path = self.store.root / ".opencode" / "opencode.db"
        if db_path.is_file():
            sessions = self._read_sessions(db_path)
            for session in sessions:
                items.append({
                    "type": "session",
                    "key": f"opencode-session-{session['id'][:8]}",
                    "source": ".opencode/opencode.db",
                    "content": session.get("summary", ""),
                })

        # 3. Skills
        skills_dir = self.store.root / ".opencode" / "skills"
        if skills_dir.is_dir():
            for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
                items.append({
                    "type": "skill",
                    "key": skill_md.parent.name,
                    "source": f".opencode/skills/{skill_md.parent.name}/SKILL.md",
                    "content": skill_md.read_text(),
                })

        if dry_run:
            return {"items": items, "imported": 0, "dry_run": True}

        imported = 0
        for item in items:
            if item["type"] == "skill":
                self.store.set_skill(
                    item["key"],
                    item["content"],
                    agent=f"import:opencode ({get_author()})",
                )
                imported += 1
            elif item["type"] == "knowledge":
                self.store.set_knowledge(
                    item["key"],
                    item["content"],
                    author=f"import:opencode ({get_author()})",
                )
                imported += 1

        return {"items": items, "imported": imported, "dry_run": False}

    def _read_sessions(self, db_path: Path) -> list[dict]:
        """Read recent sessions from OpenCode SQLite DB. Read-only."""
        try:
            import sqlite3

            conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC LIMIT 20"
            )
            sessions = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return sessions
        except Exception:
            return []

    def export_context(self, dry_run: bool = False) -> dict:
        """Export store content to AGENTS.md managed section and skills."""
        items: list[dict] = []
        conventions = self.store.list_conventions(scope=Scope.public)
        knowledge = self.store.list_knowledge(scope=Scope.public)
        skills = self.store.list_skills(scope=Scope.public)

        if not conventions and not knowledge and not skills:
            return {"items": [], "exported": 0, "dry_run": dry_run}

        if conventions or knowledge:
            items.append({
                "target": "AGENTS.md",
                "description": f"Managed section with {len(conventions)} conventions, {len(knowledge)} knowledge entries",
            })

        if skills:
            items.append({
                "target": ".opencode/skills/",
                "description": f"Export {len(skills)} skills as SKILL.md files",
            })

        if dry_run:
            return {"items": items, "exported": 0, "dry_run": True}

        exported = 0

        if conventions or knowledge:
            agents_md_path = self.store.root / "AGENTS.md"
            existing = agents_md_path.read_text() if agents_md_path.is_file() else ""
            # Conventions first, then knowledge
            entries: list[tuple[str, str]] = []
            for e in conventions:
                entries.append((f"convention: {e.key}", e.content))
            for e in knowledge:
                if e.key != "project-instructions":
                    entries.append((e.key, e.content))
            result = write_agents_md_section(existing, entries)
            agents_md_path.write_text(result)
            exported += 1

        if skills:
            skills_dir = self.store.root / ".opencode" / "skills"
            for skill in skills:
                skill_out = skills_dir / skill.name
                skill_out.mkdir(parents=True, exist_ok=True)
                (skill_out / "SKILL.md").write_text(skill.content)
                exported += 1

        return {"items": items, "exported": exported, "dry_run": False}

    def mcp_config_path(self) -> Path:
        return self.store.root / "opencode.json"

    def register_mcp(self, local: bool = False) -> dict:
        return register_mcp_json(self.mcp_config_path(), caller_name="mcp:opencode", local=local)

    def unregister_mcp(self) -> dict:
        return unregister_mcp_json(self.mcp_config_path())
