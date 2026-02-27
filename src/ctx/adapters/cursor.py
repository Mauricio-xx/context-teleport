"""Cursor adapter: import/export .cursor/rules/*.mdc, .cursorrules, MCP registration."""

from __future__ import annotations

from pathlib import Path

from ctx.adapters._mcp_reg import register_mcp_json, unregister_mcp_json
from ctx.core.frontmatter import build_frontmatter, parse_frontmatter
from ctx.core.scope import Scope
from ctx.core.store import ContextStore
from ctx.utils.paths import get_author

# Keep backwards-compatible aliases
parse_mdc = parse_frontmatter
format_mdc = build_frontmatter


class CursorAdapter:
    name = "cursor"

    def __init__(self, store: ContextStore) -> None:
        self.store = store

    def detect(self) -> bool:
        if (self.store.root / ".cursor").is_dir():
            return True
        if (self.store.root / ".cursorrules").is_file():
            return True
        return False

    def import_context(self, dry_run: bool = False) -> dict:
        items: list[dict] = []

        # .cursor/rules/*.mdc
        rules_dir = self.store.root / ".cursor" / "rules"
        if rules_dir.is_dir():
            for f in sorted(rules_dir.glob("*.mdc")):
                metadata, body = parse_mdc(f.read_text())
                items.append({
                    "type": "knowledge",
                    "key": f"cursor-rule-{f.stem}",
                    "source": f".cursor/rules/{f.name}",
                    "content": body,
                    "metadata": metadata,
                })

        # .cursorrules (legacy)
        cursorrules = self.store.root / ".cursorrules"
        if cursorrules.is_file():
            items.append({
                "type": "knowledge",
                "key": "cursorrules",
                "source": ".cursorrules",
                "content": cursorrules.read_text().strip(),
            })

        # .cursor/skills/*/SKILL.md
        skills_dir = self.store.root / ".cursor" / "skills"
        if skills_dir.is_dir():
            for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
                items.append({
                    "type": "skill",
                    "key": skill_md.parent.name,
                    "source": f".cursor/skills/{skill_md.parent.name}/SKILL.md",
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
                    agent=f"import:cursor ({get_author()})",
                )
            else:
                self.store.set_knowledge(
                    item["key"],
                    item["content"],
                    author=f"import:cursor ({get_author()})",
                )
            imported += 1

        return {"items": items, "imported": imported, "dry_run": False}

    def export_context(self, dry_run: bool = False) -> dict:
        items: list[dict] = []
        conventions = self.store.list_conventions(scope=Scope.public)
        knowledge = self.store.list_knowledge(scope=Scope.public)
        skills = self.store.list_skills(scope=Scope.public)

        if not conventions and not knowledge and not skills:
            return {"items": [], "exported": 0, "dry_run": dry_run}

        if conventions:
            items.append({
                "target": ".cursor/rules/",
                "description": f"Export {len(conventions)} conventions as Cursor MDC rules",
            })

        if knowledge:
            items.append({
                "target": ".cursor/rules/",
                "description": f"Export {len(knowledge)} entries as Cursor MDC rules",
            })

        if skills:
            items.append({
                "target": ".cursor/skills/",
                "description": f"Export {len(skills)} skills as SKILL.md files",
            })

        if dry_run:
            return {"items": items, "exported": 0, "dry_run": True}

        exported = 0
        rules_dir = self.store.root / ".cursor" / "rules"

        # Export conventions as MDC rules
        if conventions:
            rules_dir.mkdir(parents=True, exist_ok=True)
            for entry in conventions:
                metadata = {
                    "description": f"Team convention: {entry.key}",
                    "alwaysApply": True,
                }
                mdc_content = format_mdc(metadata, entry.content)
                rule_path = rules_dir / f"ctx-convention-{entry.key}.mdc"
                rule_path.write_text(mdc_content)
                exported += 1

        # Export knowledge as MDC rules
        if knowledge:
            rules_dir.mkdir(parents=True, exist_ok=True)
            for entry in knowledge:
                if entry.key == "project-instructions":
                    continue
                metadata = {
                    "description": f"Team context: {entry.key}",
                    "alwaysApply": True,
                }
                mdc_content = format_mdc(metadata, entry.content)
                rule_path = rules_dir / f"ctx-{entry.key}.mdc"
                rule_path.write_text(mdc_content)
                exported += 1

        # Export skills
        if skills:
            skills_dir = self.store.root / ".cursor" / "skills"
            for skill in skills:
                skill_out = skills_dir / skill.name
                skill_out.mkdir(parents=True, exist_ok=True)
                (skill_out / "SKILL.md").write_text(skill.content)
                exported += 1

        return {"items": items, "exported": exported, "dry_run": False}

    def mcp_config_path(self) -> Path:
        return self.store.root / ".cursor" / "mcp.json"

    def register_mcp(self, local: bool = False) -> dict:
        return register_mcp_json(self.mcp_config_path(), caller_name="mcp:cursor", local=local)

    def unregister_mcp(self) -> dict:
        return unregister_mcp_json(self.mcp_config_path())
