"""EDA importer registry: auto-detection and lookup."""

from __future__ import annotations

from pathlib import Path

from ctx.eda.parsers.base import EdaImporter, ImportItem
from ctx.eda.parsers.drc import MagicDrcParser
from ctx.eda.parsers.librelane import LibreLaneConfigParser
from ctx.eda.parsers.liberty import LibertyParser
from ctx.eda.parsers.lvs import NetgenLvsParser
from ctx.eda.parsers.metrics import LibreLaneMetricsParser
from ctx.eda.parsers.orfs import OrfsConfigParser

_IMPORTERS: dict[str, type] = {
    "librelane-config": LibreLaneConfigParser,
    "librelane-metrics": LibreLaneMetricsParser,
    "magic-drc": MagicDrcParser,
    "netgen-lvs": NetgenLvsParser,
    "orfs-config": OrfsConfigParser,
    "liberty": LibertyParser,
}


def get_importer(name: str) -> EdaImporter | None:
    """Get an importer by name."""
    cls = _IMPORTERS.get(name)
    if cls is None:
        return None
    return cls()


def auto_detect_importer(path: Path) -> EdaImporter | None:
    """Try all importers and return the first one that can parse the path."""
    path = Path(path)
    for cls in _IMPORTERS.values():
        imp = cls()
        if imp.can_parse(path):
            return imp
    return None


def list_importers() -> list[str]:
    """Return available importer names."""
    return list(_IMPORTERS.keys())


__all__ = [
    "EdaImporter",
    "ImportItem",
    "auto_detect_importer",
    "get_importer",
    "list_importers",
]
