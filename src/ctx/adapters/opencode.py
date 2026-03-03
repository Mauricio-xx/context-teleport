"""OpenCode adapter: import/export from AGENTS.md, sessions, agents, commands, MCP registration."""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

from ctx.adapters._agents_md import parse_agents_md, write_agents_md_section
from ctx.adapters._mcp_reg import register_mcp_opencode, unregister_mcp_opencode
from ctx.core.scope import Scope
from ctx.core.store import ContextStore
from ctx.utils.paths import get_author, opencode_data_dir

logger = logging.getLogger(__name__)


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

        # 2. Agent definitions (.opencode/agents/ or .opencode/agent/)
        items.extend(self._read_agents())

        # 3. Command definitions (.opencode/commands/ or .opencode/command/)
        items.extend(self._read_commands())

        # 4. Session summaries from JSON data dir
        items.extend(self._read_session_summaries())

        # 5. Skills
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

    def _read_agents(self) -> list[dict]:
        """Read agent definitions from .opencode/agents/ (or .opencode/agent/)."""
        items: list[dict] = []
        for dir_name in ("agents", "agent"):
            agents_dir = self.store.root / ".opencode" / dir_name
            if not agents_dir.is_dir():
                continue
            for md_path in sorted(agents_dir.rglob("*.md")):
                rel = md_path.relative_to(agents_dir)
                # Key from relative path: python/linter.md -> opencode-agent-python-linter
                key_parts = list(rel.parent.parts) + [rel.stem]
                key = "opencode-agent-" + "-".join(key_parts)
                items.append({
                    "type": "knowledge",
                    "key": key,
                    "source": f".opencode/{dir_name}/{rel}",
                    "content": md_path.read_text(),
                })
        return items

    def _read_commands(self) -> list[dict]:
        """Read command definitions from .opencode/commands/ (or .opencode/command/)."""
        items: list[dict] = []
        for dir_name in ("commands", "command"):
            cmds_dir = self.store.root / ".opencode" / dir_name
            if not cmds_dir.is_dir():
                continue
            for md_path in sorted(cmds_dir.rglob("*.md")):
                rel = md_path.relative_to(cmds_dir)
                key_parts = list(rel.parent.parts) + [rel.stem]
                key = "opencode-command-" + "-".join(key_parts)
                items.append({
                    "type": "knowledge",
                    "key": key,
                    "source": f".opencode/{dir_name}/{rel}",
                    "content": md_path.read_text(),
                })
        return items

    def _get_project_id(self) -> str | None:
        """Get the git root commit hash, used by OpenCode as project ID."""
        try:
            from git import InvalidGitRepositoryError, Repo

            repo = Repo(self.store.root, search_parent_directories=True)
            root_commits = repo.git.rev_list("HEAD", max_parents=0).strip().split("\n")
            return root_commits[0] if root_commits else None
        except (InvalidGitRepositoryError, Exception):
            return None

    def _read_session_summaries(self) -> list[dict]:
        """Read recent session summaries from OpenCode JSON data directory."""
        project_id = self._get_project_id()
        if not project_id:
            return []

        sessions_dir = opencode_data_dir() / "storage" / "session" / project_id
        if not sessions_dir.is_dir():
            return []

        # Collect session files with their timestamps for sorting
        session_entries: list[tuple[float, Path]] = []
        for json_path in sessions_dir.glob("*.json"):
            try:
                data = json.loads(json_path.read_text())
                # Use time.updated if available, else file mtime
                ts = data.get("time", {}).get("updated", 0)
                if not ts:
                    ts = json_path.stat().st_mtime
                session_entries.append((ts, json_path))
            except (json.JSONDecodeError, OSError):
                continue

        # Sort by timestamp descending, limit to 20
        session_entries.sort(key=lambda x: x[0], reverse=True)
        session_entries = session_entries[:20]

        items: list[dict] = []
        for _ts, json_path in session_entries:
            try:
                data = json.loads(json_path.read_text())
                session_id = json_path.stem
                title = data.get("title", "Untitled session")
                summary = data.get("summary", {})
                time_info = data.get("time", {})

                # Format content
                lines = [f"## {title}"]
                if time_info.get("created"):
                    lines.append(f"Created: {time_info['created']}")
                if summary:
                    additions = summary.get("additions", 0)
                    deletions = summary.get("deletions", 0)
                    files = summary.get("files", 0)
                    lines.append(f"Changes: +{additions}/-{deletions} across {files} files")

                items.append({
                    "type": "knowledge",
                    "key": f"opencode-session-{session_id[:8]}",
                    "source": f"opencode/storage/session/{project_id}/{json_path.name}",
                    "content": "\n".join(lines),
                })
            except (json.JSONDecodeError, OSError, KeyError):
                continue

        return items

    def export_context(self, dry_run: bool = False) -> dict:
        """Export store content to AGENTS.md managed section and skills."""
        items: list[dict] = []
        conventions = self.store.list_conventions(scope=Scope.public)
        knowledge = self.store.list_knowledge(scope=Scope.public)
        decisions = self.store.list_decisions(scope=Scope.public)
        skills = self.store.list_skills(scope=Scope.public)

        if not conventions and not knowledge and not decisions and not skills:
            return {"items": [], "exported": 0, "dry_run": dry_run}

        if conventions or knowledge or decisions:
            items.append({
                "target": "AGENTS.md",
                "description": (
                    f"Managed section with {len(conventions)} conventions, "
                    f"{len(knowledge)} knowledge entries, {len(decisions)} decisions"
                ),
            })

        if skills:
            items.append({
                "target": ".opencode/skills/",
                "description": f"Export {len(skills)} skills as SKILL.md files",
            })

        if dry_run:
            return {"items": items, "exported": 0, "dry_run": True}

        exported = 0

        if conventions or knowledge or decisions:
            agents_md_path = self.store.root / "AGENTS.md"
            existing = agents_md_path.read_text() if agents_md_path.is_file() else ""
            # Conventions first, then knowledge, then decisions
            entries: list[tuple[str, str]] = []
            for e in conventions:
                entries.append((f"convention: {e.key}", e.content))
            for e in knowledge:
                if e.key != "project-instructions":
                    entries.append((e.key, e.content))
            if decisions:
                decision_lines = []
                for d in decisions:
                    decision_lines.append(f"- **{d.id:04d}** {d.title} ({d.status.value})")
                entries.append(("decisions", "\n".join(decision_lines)))
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
        return register_mcp_opencode(self.mcp_config_path(), caller_name="mcp:opencode", local=local)

    def unregister_mcp(self) -> dict:
        return unregister_mcp_opencode(self.mcp_config_path())
