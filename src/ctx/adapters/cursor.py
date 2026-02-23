"""Cursor adapter: import/export .cursor/rules/*.mdc, .cursorrules, MCP registration."""

from __future__ import annotations

import re
from pathlib import Path

from ctx.adapters._mcp_reg import register_mcp_json, unregister_mcp_json
from ctx.core.scope import Scope
from ctx.core.store import ContextStore
from ctx.utils.paths import get_author


def parse_mdc(text: str) -> tuple[dict, str]:
    """Parse MDC format: YAML frontmatter + markdown body.

    Returns (metadata_dict, body_content).
    """
    if not text.startswith("---"):
        return {}, text

    # Find closing ---
    end_match = re.search(r"\n---\s*\n", text[3:])
    if not end_match:
        return {}, text

    frontmatter_text = text[3 : 3 + end_match.start()]
    body = text[3 + end_match.end() :]

    # Simple YAML parsing (key: value lines)
    metadata: dict = {}
    for line in frontmatter_text.strip().split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            # Handle booleans
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False
            # Handle arrays like ["**/*.py"]
            elif value.startswith("[") and value.endswith("]"):
                value = [v.strip().strip("\"'") for v in value[1:-1].split(",") if v.strip()]
            metadata[key] = value

    return metadata, body.strip()


def format_mdc(metadata: dict, content: str) -> str:
    """Format as MDC: YAML frontmatter + markdown body."""
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, list):
            formatted = ", ".join(f'"{v}"' for v in value)
            lines.append(f"{key}: [{formatted}]")
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    lines.append("")
    lines.append(content.strip())
    lines.append("")
    return "\n".join(lines)


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

        if dry_run:
            return {"items": items, "imported": 0, "dry_run": True}

        imported = 0
        for item in items:
            self.store.set_knowledge(
                item["key"],
                item["content"],
                author=f"import:cursor ({get_author()})",
            )
            imported += 1

        return {"items": items, "imported": imported, "dry_run": False}

    def export_context(self, dry_run: bool = False) -> dict:
        items: list[dict] = []
        knowledge = self.store.list_knowledge(scope=Scope.public)

        if not knowledge:
            return {"items": [], "exported": 0, "dry_run": dry_run}

        items.append({
            "target": ".cursor/rules/",
            "description": f"Export {len(knowledge)} entries as Cursor MDC rules",
        })

        if dry_run:
            return {"items": items, "exported": 0, "dry_run": True}

        rules_dir = self.store.root / ".cursor" / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)

        exported = 0
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

        return {"items": items, "exported": exported, "dry_run": False}

    def mcp_config_path(self) -> Path:
        return self.store.root / ".cursor" / "mcp.json"

    def register_mcp(self) -> dict:
        return register_mcp_json(self.mcp_config_path())

    def unregister_mcp(self) -> dict:
        return unregister_mcp_json(self.mcp_config_path())
