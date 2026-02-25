"""Claude Code adapter: read/write MEMORY.md, CLAUDE.md, rules, MCP registration."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from ctx.adapters._mcp_reg import register_mcp_json, unregister_mcp_json
from ctx.core.scope import Scope
from ctx.core.store import ContextStore
from ctx.utils.paths import (
    claude_home,
    find_claude_project_dir,
    get_author,
)


CTX_SECTION_MARKER = "## Team Context (managed by ctx)"
CTX_SECTION_END = "<!-- end ctx managed -->"


class ClaudeCodeAdapter:
    """Adapter for Claude Code: imports from and exports to Claude Code internals."""

    name = "claude_code"

    def __init__(self, store: ContextStore) -> None:
        self.store = store

    def detect(self) -> bool:
        """Check if Claude Code is installed."""
        home = claude_home()
        if not home.is_dir():
            return False
        # Check for claude binary
        if shutil.which("claude") is not None:
            return True
        return home.is_dir()

    def _find_project_dir(self) -> Path | None:
        return find_claude_project_dir(self.store.root)

    def _read_memory_md(self) -> str | None:
        """Read MEMORY.md from Claude Code project directory."""
        project_dir = self._find_project_dir()
        if project_dir is None:
            return None
        memory_dir = project_dir / "memory"
        if not memory_dir.is_dir():
            return None
        memory_file = memory_dir / "MEMORY.md"
        if memory_file.is_file():
            return memory_file.read_text()
        return None

    def _read_claude_md(self) -> str | None:
        """Read project CLAUDE.md."""
        claude_md = self.store.root / "CLAUDE.md"
        if claude_md.is_file():
            return claude_md.read_text()
        return None

    def _read_rules(self) -> list[tuple[str, str]]:
        """Read .claude/rules/*.md files."""
        rules_dir = self.store.root / ".claude" / "rules"
        if not rules_dir.is_dir():
            return []
        result = []
        for f in sorted(rules_dir.glob("*.md")):
            result.append((f.stem, f.read_text()))
        return result

    def _read_skills(self) -> list[tuple[str, str]]:
        """Read .claude/skills/*/SKILL.md files."""
        skills_dir = self.store.root / ".claude" / "skills"
        if not skills_dir.is_dir():
            return []
        result = []
        for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
            result.append((skill_md.parent.name, skill_md.read_text()))
        return result

    def _parse_memory_into_knowledge(self, memory_text: str) -> list[tuple[str, str]]:
        """Parse MEMORY.md content into knowledge entries.

        Splits by ## headers into separate entries. Nested ### and ####
        headers are kept as content under their parent ## section.
        If no ## headers found, tries # headers.
        If no headers at all, stores as a single 'memory' entry.
        """
        sections: list[tuple[str, str]] = []
        current_key = ""
        current_lines: list[str] = []

        for line in memory_text.split("\n"):
            # Match ## headers as section boundaries (### and #### are nested content)
            header_match = re.match(r"^(#{1,2})\s+(.+)", line)
            if header_match and len(header_match.group(1)) <= 2:
                if current_key and current_lines:
                    sections.append((current_key, "\n".join(current_lines).strip()))
                raw = header_match.group(2).strip()
                current_key = _slugify(raw)
                current_lines = [line]
            else:
                current_lines.append(line)

        if current_key and current_lines:
            sections.append((current_key, "\n".join(current_lines).strip()))

        if not sections and memory_text.strip():
            sections.append(("memory", memory_text.strip()))

        return sections

    def import_context(self, dry_run: bool = False) -> dict:
        """Extract from Claude Code internals into the context store."""
        items: list[dict] = []

        # Import MEMORY.md
        memory = self._read_memory_md()
        if memory:
            entries = self._parse_memory_into_knowledge(memory)
            for key, content in entries:
                items.append({
                    "type": "knowledge",
                    "key": key,
                    "source": "MEMORY.md",
                    "content": content,
                })

        # Import CLAUDE.md (as conventions/project-instructions)
        claude_md = self._read_claude_md()
        if claude_md:
            # Strip any existing ctx-managed section
            clean = _strip_ctx_section(claude_md)
            if clean.strip():
                items.append({
                    "type": "knowledge",
                    "key": "project-instructions",
                    "source": "CLAUDE.md",
                    "content": clean.strip(),
                })

        # Import rules
        rules = self._read_rules()
        for rule_name, rule_content in rules:
            items.append({
                "type": "knowledge",
                "key": f"rule-{rule_name}",
                "source": f".claude/rules/{rule_name}.md",
                "content": rule_content,
            })

        # Import skills
        skills = self._read_skills()
        for skill_name, skill_content in skills:
            items.append({
                "type": "skill",
                "key": skill_name,
                "source": f".claude/skills/{skill_name}/SKILL.md",
                "content": skill_content,
            })

        if dry_run:
            return {"items": items, "imported": 0, "dry_run": True}

        # Write to store
        imported = 0
        for item in items:
            if item["type"] == "skill":
                self.store.set_skill(
                    item["key"],
                    item["content"],
                    agent=f"import:claude-code ({get_author()})",
                )
            else:
                self.store.set_knowledge(
                    item["key"],
                    item["content"],
                    author=f"import:claude-code ({get_author()})",
                )
            imported += 1

        return {"items": items, "imported": imported, "dry_run": False}

    def export_context(self, dry_run: bool = False) -> dict:
        """Inject store content into Claude Code locations (public entries only)."""
        items: list[dict] = []
        knowledge = self.store.list_knowledge(scope=Scope.public)
        decisions = self.store.list_decisions(scope=Scope.public)
        skills = self.store.list_skills(scope=Scope.public)

        if not knowledge and not decisions and not skills:
            return {"items": [], "exported": 0, "dry_run": dry_run}

        # Build the managed section for CLAUDE.md
        section_lines = [CTX_SECTION_MARKER, ""]
        if knowledge:
            for entry in knowledge:
                # Skip entries that came from CLAUDE.md itself
                if entry.key == "project-instructions":
                    continue
                section_lines.append(f"### {entry.key}")
                section_lines.append(entry.content.strip())
                section_lines.append("")

        if decisions:
            section_lines.append("### Decisions")
            for d in decisions:
                section_lines.append(f"- **{d.id:04d}** {d.title} ({d.status.value})")
            section_lines.append("")

        section_lines.append(CTX_SECTION_END)
        managed_section = "\n".join(section_lines)

        items.append({
            "target": "CLAUDE.md",
            "description": f"Managed section with {len(knowledge)} knowledge entries, {len(decisions)} decisions",
        })

        # Build MEMORY.md content
        memory_lines = ["# Team Context (synced by ctx)", ""]
        for entry in knowledge:
            if entry.key == "project-instructions":
                continue
            memory_lines.append(f"## {entry.key}")
            memory_lines.append(entry.content.strip())
            memory_lines.append("")
        memory_content = "\n".join(memory_lines)

        project_dir = self._find_project_dir()
        if project_dir:
            items.append({
                "target": f"{project_dir}/memory/MEMORY.md",
                "description": "Updated MEMORY.md with store knowledge",
            })

        if skills:
            items.append({
                "target": ".claude/skills/",
                "description": f"Export {len(skills)} skills as SKILL.md files",
            })

        if dry_run:
            return {"items": items, "exported": 0, "dry_run": True}

        # Write CLAUDE.md
        exported = 0
        claude_md_path = self.store.root / "CLAUDE.md"
        if claude_md_path.is_file():
            existing = claude_md_path.read_text()
            clean = _strip_ctx_section(existing)
            claude_md_path.write_text(clean.rstrip() + "\n\n" + managed_section + "\n")
        else:
            claude_md_path.write_text(managed_section + "\n")
        exported += 1

        # Write MEMORY.md
        if project_dir:
            memory_dir = project_dir / "memory"
            memory_dir.mkdir(parents=True, exist_ok=True)
            memory_file = memory_dir / "MEMORY.md"
            if memory_file.is_file():
                existing_memory = memory_file.read_text()
                # Append or replace team context section
                if "# Team Context (synced by ctx)" in existing_memory:
                    # Replace everything from that header onward
                    idx = existing_memory.index("# Team Context (synced by ctx)")
                    memory_file.write_text(existing_memory[:idx] + memory_content)
                else:
                    memory_file.write_text(existing_memory.rstrip() + "\n\n" + memory_content)
            else:
                memory_file.write_text(memory_content)
            exported += 1

        # Write skills
        if skills:
            skills_dir = self.store.root / ".claude" / "skills"
            for skill in skills:
                skill_out = skills_dir / skill.name
                skill_out.mkdir(parents=True, exist_ok=True)
                (skill_out / "SKILL.md").write_text(skill.content)
                exported += 1

        return {"items": items, "exported": exported, "dry_run": False}

    def mcp_config_path(self) -> Path:
        """Return the path to Claude Code's MCP config file."""
        return self.store.root / ".claude" / "mcp.json"

    def register_mcp_server(self, local: bool = False) -> dict:
        """Register the ctx-mcp server in .claude/mcp.json."""
        return register_mcp_json(self.mcp_config_path(), caller_name="mcp:claude-code", local=local)

    def unregister_mcp_server(self) -> dict:
        """Remove the ctx-mcp server from .claude/mcp.json."""
        return unregister_mcp_json(self.mcp_config_path())

    def register_mcp(self, local: bool = False) -> dict:
        """Register ctx-mcp (AdapterProtocol method)."""
        return self.register_mcp_server(local=local)

    def unregister_mcp(self) -> dict:
        """Remove ctx-mcp (AdapterProtocol method)."""
        return self.unregister_mcp_server()


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "untitled"


def _strip_ctx_section(text: str) -> str:
    """Remove the ctx-managed section from a file."""
    if CTX_SECTION_MARKER not in text:
        return text
    before = text[: text.index(CTX_SECTION_MARKER)]
    if CTX_SECTION_END in text:
        after = text[text.index(CTX_SECTION_END) + len(CTX_SECTION_END) :]
    else:
        after = ""
    return before + after
