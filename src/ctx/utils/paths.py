"""Path utilities for context store and Claude Code integration."""

from __future__ import annotations

import os
import platform
import re
from pathlib import Path


STORE_DIR = ".context-teleport"


def find_project_root(start: Path | None = None) -> Path | None:
    """Walk up from start to find a directory containing .context-teleport/ or .git/."""
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        if (parent / STORE_DIR).is_dir():
            return parent
        if (parent / ".git").exists():
            return parent
    return None


def store_path(project_root: Path | None = None) -> Path:
    """Return the .context-teleport/ path for a project."""
    root = project_root or find_project_root()
    if root is None:
        raise FileNotFoundError("Not inside a project with a context store or git repo")
    return root / STORE_DIR


def get_machine_name() -> str:
    return platform.node() or "unknown"


def get_username() -> str:
    return os.environ.get("USER", os.environ.get("USERNAME", "unknown"))


def get_author() -> str:
    return f"{get_username()}@{get_machine_name()}"


# Claude Code path resolution


def claude_home() -> Path:
    """Return the Claude Code home directory (~/.claude/)."""
    return Path.home() / ".claude"


def claude_projects_dir() -> Path:
    return claude_home() / "projects"


def path_hash(project_path: Path) -> str:
    """Compute the path hash Claude Code uses for project directories.

    Claude Code stores project-specific memory under
    ~/.claude/projects/-<path-with-dashes>/
    where the directory name is the absolute project path with '/' replaced by '-'.
    """
    abs_path = str(project_path.resolve())
    return abs_path.replace("/", "-")


def find_claude_project_dir(project_root: Path | None = None) -> Path | None:
    """Find the Claude Code project memory directory for the given project."""
    root = project_root or find_project_root()
    if root is None:
        return None
    projects = claude_projects_dir()
    if not projects.is_dir():
        return None
    hashed = path_hash(root)
    candidate = projects / hashed
    if candidate.is_dir():
        return candidate
    # Fallback: scan for directories that contain the project name
    project_name = root.name
    for d in projects.iterdir():
        if d.is_dir() and project_name in d.name:
            return d
    return None


def sanitize_key(key: str) -> str:
    """Sanitize a key for use as a filename (no path traversal, no special chars)."""
    key = key.strip().lower()
    key = re.sub(r"[^\w\-]", "-", key)
    key = re.sub(r"-+", "-", key).strip("-")
    if not key:
        raise ValueError("Key cannot be empty")
    return key
