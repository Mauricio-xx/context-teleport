"""Codex (OpenAI) adapter: import/export from AGENTS.md and .codex/ directory."""

from __future__ import annotations

import shutil
from pathlib import Path

from ctx.adapters._agents_md import parse_agents_md, write_agents_md_section
from ctx.core.scope import Scope
from ctx.core.store import ContextStore
from ctx.utils.paths import get_author


class CodexAdapter:
    name = "codex"

    def __init__(self, store: ContextStore) -> None:
        self.store = store

    def detect(self) -> bool:
        if shutil.which("codex") is not None:
            return True
        if (self.store.root / ".codex").is_dir():
            return True
        return False

    def import_context(self, dry_run: bool = False) -> dict:
        items: list[dict] = []

        # AGENTS.md
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

        # .codex/instructions.md
        instructions = self.store.root / ".codex" / "instructions.md"
        if instructions.is_file():
            items.append({
                "type": "knowledge",
                "key": "codex-instructions",
                "source": ".codex/instructions.md",
                "content": instructions.read_text().strip(),
            })

        if dry_run:
            return {"items": items, "imported": 0, "dry_run": True}

        imported = 0
        for item in items:
            self.store.set_knowledge(
                item["key"],
                item["content"],
                author=f"import:codex ({get_author()})",
            )
            imported += 1

        return {"items": items, "imported": imported, "dry_run": False}

    def export_context(self, dry_run: bool = False) -> dict:
        items: list[dict] = []
        knowledge = self.store.list_knowledge(scope=Scope.public)

        if not knowledge:
            return {"items": [], "exported": 0, "dry_run": dry_run}

        items.append({
            "target": "AGENTS.md",
            "description": f"Managed section with {len(knowledge)} entries",
        })

        if dry_run:
            return {"items": items, "exported": 0, "dry_run": True}

        # Write AGENTS.md
        agents_md_path = self.store.root / "AGENTS.md"
        existing = agents_md_path.read_text() if agents_md_path.is_file() else ""
        entries = [(e.key, e.content) for e in knowledge if e.key != "project-instructions"]
        agents_md_path.write_text(write_agents_md_section(existing, entries))

        return {"items": items, "exported": 1, "dry_run": False}

    def mcp_config_path(self) -> Path | None:
        # Codex MCP support is TBD
        return None

    def register_mcp(self, local: bool = False) -> dict:
        return {"status": "unsupported", "reason": "Codex does not yet support MCP"}

    def unregister_mcp(self) -> dict:
        return {"status": "unsupported", "reason": "Codex does not yet support MCP"}
