"""YAML frontmatter parser/builder for SKILL.md and similar formats.

Handles the standard `---`-delimited YAML frontmatter block used by
SKILL.md (agent skills), Cursor MDC files, and other markdown-with-metadata
formats. Simple key: value parsing -- no PyYAML dependency needed.
"""

from __future__ import annotations

import re


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter + markdown body.

    Returns (metadata_dict, body_content). If no frontmatter is present,
    returns ({}, original_text).
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


def build_frontmatter(metadata: dict, body: str) -> str:
    """Build a frontmatter document from metadata dict and body text.

    Returns the complete document string with ``---`` delimiters.
    """
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
    lines.append(body.strip())
    lines.append("")
    return "\n".join(lines)
