"""Shared AGENTS.md parsing and writing utilities.

Both OpenCode and Codex use AGENTS.md (AAIF standard). This module provides
common parsing and managed-section writing for both adapters.
"""

from __future__ import annotations

import re

CTX_AGENTS_START = "<!-- ctx:start -->"
CTX_AGENTS_END = "<!-- ctx:end -->"


def parse_agents_md(text: str) -> list[tuple[str, str]]:
    """Parse AGENTS.md sections into (key, content) pairs.

    Splits by ## headers. Skips any ctx-managed section (between markers).
    Returns list of (slugified_key, raw_section_content) pairs.
    """
    # Remove ctx-managed section first
    clean = _strip_ctx_section(text)

    sections: list[tuple[str, str]] = []
    current_key = ""
    current_lines: list[str] = []

    for line in clean.split("\n"):
        header_match = re.match(r"^##\s+(.+)", line)
        if header_match:
            if current_key and current_lines:
                sections.append((current_key, "\n".join(current_lines).strip()))
            raw = header_match.group(1).strip()
            current_key = _slugify(raw)
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_key and current_lines:
        sections.append((current_key, "\n".join(current_lines).strip()))

    # If no ## headers found, try # headers
    if not sections:
        current_key = ""
        current_lines = []
        for line in clean.split("\n"):
            header_match = re.match(r"^#\s+(.+)", line)
            if header_match:
                if current_key and current_lines:
                    sections.append((current_key, "\n".join(current_lines).strip()))
                raw = header_match.group(1).strip()
                current_key = _slugify(raw)
                current_lines = [line]
            else:
                current_lines.append(line)
        if current_key and current_lines:
            sections.append((current_key, "\n".join(current_lines).strip()))

    # If still nothing, store as a single entry
    if not sections and clean.strip():
        sections.append(("agents", clean.strip()))

    return sections


def write_agents_md_section(existing: str, entries: list[tuple[str, str]]) -> str:
    """Insert or replace ctx-managed section in AGENTS.md.

    Args:
        existing: Current content of AGENTS.md (or empty string if new file)
        entries: List of (key, content) pairs to include in managed section

    Returns:
        Updated AGENTS.md content with managed section.
    """
    managed_lines = [CTX_AGENTS_START, "", "## Team Context (synced by ctx)", ""]

    for key, content in entries:
        managed_lines.append(f"### {key}")
        managed_lines.append(content.strip())
        managed_lines.append("")

    managed_lines.append(CTX_AGENTS_END)
    managed_section = "\n".join(managed_lines)

    # Replace existing managed section or append
    clean = _strip_ctx_section(existing)
    if clean.strip():
        return clean.rstrip() + "\n\n" + managed_section + "\n"
    else:
        return managed_section + "\n"


def _strip_ctx_section(text: str) -> str:
    """Remove the ctx-managed section from text."""
    if CTX_AGENTS_START not in text:
        return text
    before = text[: text.index(CTX_AGENTS_START)]
    if CTX_AGENTS_END in text:
        after = text[text.index(CTX_AGENTS_END) + len(CTX_AGENTS_END) :]
    else:
        after = ""
    return before + after


def _slugify(text: str) -> str:
    """Convert text to a key-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "untitled"
