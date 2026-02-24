"""Gemini adapter: import/export from .gemini/ rules and instructions."""

from __future__ import annotations

from pathlib import Path

from ctx.adapters._mcp_reg import register_mcp_json, unregister_mcp_json
from ctx.core.scope import Scope
from ctx.core.store import ContextStore
from ctx.utils.paths import get_author


class GeminiAdapter:
    name = "gemini"

    def __init__(self, store: ContextStore) -> None:
        self.store = store

    def detect(self) -> bool:
        if (self.store.root / ".gemini").is_dir():
            return True
        if (self.store.root / "GEMINI.md").is_file():
            return True
        return False

    def import_context(self, dry_run: bool = False) -> dict:
        items: list[dict] = []

        # .gemini/rules/*.md
        rules_dir = self.store.root / ".gemini" / "rules"
        if rules_dir.is_dir():
            for f in sorted(rules_dir.glob("*.md")):
                items.append({
                    "type": "knowledge",
                    "key": f"gemini-rule-{f.stem}",
                    "source": f".gemini/rules/{f.name}",
                    "content": f.read_text().strip(),
                })

        # .gemini/STYLEGUIDE.md
        styleguide = self.store.root / ".gemini" / "STYLEGUIDE.md"
        if styleguide.is_file():
            items.append({
                "type": "knowledge",
                "key": "gemini-styleguide",
                "source": ".gemini/STYLEGUIDE.md",
                "content": styleguide.read_text().strip(),
            })

        # GEMINI.md
        gemini_md = self.store.root / "GEMINI.md"
        if gemini_md.is_file():
            items.append({
                "type": "knowledge",
                "key": "gemini-instructions",
                "source": "GEMINI.md",
                "content": gemini_md.read_text().strip(),
            })

        if dry_run:
            return {"items": items, "imported": 0, "dry_run": True}

        imported = 0
        for item in items:
            self.store.set_knowledge(
                item["key"],
                item["content"],
                author=f"import:gemini ({get_author()})",
            )
            imported += 1

        return {"items": items, "imported": imported, "dry_run": False}

    def export_context(self, dry_run: bool = False) -> dict:
        items: list[dict] = []
        knowledge = self.store.list_knowledge(scope=Scope.public)

        if not knowledge:
            return {"items": [], "exported": 0, "dry_run": dry_run}

        items.append({
            "target": ".gemini/rules/",
            "description": f"Export {len(knowledge)} entries as Gemini rule files",
        })

        if dry_run:
            return {"items": items, "exported": 0, "dry_run": True}

        rules_dir = self.store.root / ".gemini" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        exported = 0
        for entry in knowledge:
            if entry.key == "project-instructions":
                continue
            rule_path = rules_dir / f"ctx-{entry.key}.md"
            rule_path.write_text(entry.content.strip() + "\n")
            exported += 1

        return {"items": items, "exported": exported, "dry_run": False}

    def mcp_config_path(self) -> Path:
        return self.store.root / ".gemini" / "settings.json"

    def register_mcp(self, local: bool = False) -> dict:
        return register_mcp_json(self.mcp_config_path(), caller_name="mcp:gemini", local=local)

    def unregister_mcp(self) -> dict:
        return unregister_mcp_json(self.mcp_config_path())
