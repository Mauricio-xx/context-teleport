"""Tests for ArtifactImporter protocol and ImportItem."""

from pathlib import Path

from ctx.eda.parsers.base import EdaImporter, ImportItem
from ctx.importers.base import ArtifactImporter


class _DummyImporter:
    """Minimal implementation for protocol checks."""

    name = "dummy"

    def can_parse(self, path: Path) -> bool:
        return path.suffix == ".dummy"

    def parse(self, path: Path) -> list[ImportItem]:
        return [ImportItem(type="knowledge", key="k", content="c", source=str(path))]

    def describe(self) -> str:
        return "Dummy importer for tests"


class TestArtifactImporterProtocol:
    def test_isinstance_check(self):
        imp = _DummyImporter()
        assert isinstance(imp, ArtifactImporter)

    def test_also_satisfies_eda_importer(self):
        """ArtifactImporter has the same shape as EdaImporter."""
        imp = _DummyImporter()
        assert isinstance(imp, EdaImporter)

    def test_import_item_reexported(self):
        """ImportItem should be importable from ctx.importers.base."""
        from ctx.importers.base import ImportItem as ReExported

        assert ReExported is ImportItem

    def test_non_conforming_class_rejected(self):
        class Bad:
            pass

        assert not isinstance(Bad(), ArtifactImporter)
