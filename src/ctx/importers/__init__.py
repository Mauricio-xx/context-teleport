"""Artifact importer registry: built-in + entry-point plugin discovery.

The registry is **lazily loaded** -- the first call to any public function
triggers discovery.  This keeps ``context-teleport --help`` fast.

Discovery order:

1. Built-in importers from ``ctx.eda.parsers._IMPORTERS``.
2. Entry-point importers from the ``ctx.importers`` group.
   - Broken plugins are logged and skipped.
   - Name collisions are logged; last-loaded wins (entry-points override
     built-ins).
"""

from __future__ import annotations

import logging
from pathlib import Path

from ctx.importers.base import ArtifactImporter, ImportItem

logger = logging.getLogger(__name__)

_registry: dict[str, ArtifactImporter] | None = None

__all__ = [
    "ArtifactImporter",
    "ImportItem",
    "auto_detect_importer",
    "get_importer",
    "list_importers",
]


def _ensure_loaded() -> dict[str, ArtifactImporter]:
    """Populate the registry on first access."""
    global _registry  # noqa: PLW0603
    if _registry is not None:
        return _registry

    _registry = {}
    _builtin_classes: set[type] = set()

    # 1. Built-in importers from ctx.eda.parsers
    try:
        from ctx.eda.parsers import _IMPORTERS as builtin_map

        for name, cls in builtin_map.items():
            _registry[name] = cls()
            _builtin_classes.add(cls)
    except Exception as exc:
        logger.warning("Failed to load built-in EDA importers: %s", exc)

    # 2. Entry-point plugins
    try:
        from importlib.metadata import entry_points

        eps = entry_points(group="ctx.importers")
        for ep in eps:
            try:
                cls = ep.load()
                instance = cls()
                if ep.name in _registry and cls not in _builtin_classes:
                    # Only warn for genuine third-party collisions, not our
                    # own entry-points re-registering the same built-in class.
                    logger.warning(
                        "Importer '%s' from '%s' shadows existing importer",
                        ep.name,
                        ep.value,
                    )
                _registry[ep.name] = instance
            except (ImportError, ModuleNotFoundError) as err:
                logger.warning("Failed to load importer plugin '%s': %s", ep.name, err)
            except Exception as err:
                logger.warning("Failed to load importer plugin '%s': %s", ep.name, err)
    except Exception as exc:
        logger.warning("Entry-point discovery failed: %s", exc)

    return _registry


def reset_registry() -> None:
    """Clear the cached registry (for testing)."""
    global _registry  # noqa: PLW0603
    _registry = None


def get_importer(name: str) -> ArtifactImporter | None:
    """Get an importer by name, or ``None`` if not found."""
    registry = _ensure_loaded()
    return registry.get(name)


def auto_detect_importer(path: Path) -> ArtifactImporter | None:
    """Try all importers and return the first one that can parse *path*."""
    path = Path(path)
    for imp in _ensure_loaded().values():
        if imp.can_parse(path):
            return imp
    return None


def list_importers() -> list[str]:
    """Return all registered importer names."""
    return list(_ensure_loaded().keys())
