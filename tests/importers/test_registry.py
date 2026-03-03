"""Tests for the artifact importer registry (built-in + entry-point discovery)."""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from ctx.eda.parsers.base import ImportItem
from ctx.importers import (
    _ensure_loaded,
    auto_detect_importer,
    get_importer,
    list_importers,
    reset_registry,
)
from ctx.importers.base import ArtifactImporter


# -- Helpers ----------------------------------------------------------------


class _FakeImporter:
    name = "fake-web"

    def can_parse(self, path: Path) -> bool:
        return path.name == "webpack.config.js"

    def parse(self, path: Path) -> list[ImportItem]:
        return [ImportItem(type="knowledge", key="webpack", content="cfg", source=str(path))]

    def describe(self) -> str:
        return "Fake webpack config importer"


class _BadImporter:
    """Missing required methods -- not a valid ArtifactImporter."""

    name = "bad"


def _make_entry_point(name: str, cls, *, raises: Exception | None = None):
    """Build a mock entry point that loads *cls* (or raises)."""
    ep = MagicMock()
    ep.name = name
    ep.value = f"fake_pkg.{name}:{cls.__name__}" if cls else f"fake_pkg.{name}:Missing"
    if raises:
        ep.load.side_effect = raises
    else:
        ep.load.return_value = cls
    return ep


# -- Tests ------------------------------------------------------------------


class TestBuiltinDiscovery:
    def test_includes_all_eda_parsers(self):
        names = list_importers()
        expected = {
            "librelane-config",
            "librelane-metrics",
            "magic-drc",
            "netgen-lvs",
            "orfs-config",
            "liberty",
        }
        assert expected.issubset(set(names))

    def test_get_importer_returns_instance(self):
        imp = get_importer("liberty")
        assert imp is not None
        assert isinstance(imp, ArtifactImporter)

    def test_get_importer_unknown_returns_none(self):
        assert get_importer("nonexistent") is None

    def test_auto_detect_unknown_returns_none(self, tmp_path):
        f = tmp_path / "random.xyz"
        f.write_text("nope")
        assert auto_detect_importer(f) is None


class TestLazyLoading:
    def test_registry_is_none_after_reset(self):
        from ctx import importers

        reset_registry()
        assert importers._registry is None

    def test_first_access_populates(self):
        from ctx import importers

        reset_registry()
        assert importers._registry is None
        names = list_importers()
        assert importers._registry is not None
        assert len(names) > 0

    def test_second_call_reuses_cache(self):
        from ctx import importers

        _ensure_loaded()
        first = importers._registry
        _ensure_loaded()
        assert importers._registry is first


class TestEntryPointDiscovery:
    def _patch_entry_points(self, eps):
        return patch(
            "importlib.metadata.entry_points",
            return_value=eps,
        )

    def test_plugin_loaded(self):
        ep = _make_entry_point("fake-web", _FakeImporter)
        with self._patch_entry_points([ep]):
            reset_registry()
            imp = get_importer("fake-web")
        assert imp is not None
        assert imp.name == "fake-web"

    def test_broken_plugin_skipped(self, caplog):
        ep = _make_entry_point("broken", None, raises=ImportError("no module"))
        with self._patch_entry_points([ep]):
            reset_registry()
            with caplog.at_level(logging.WARNING, logger="ctx.importers"):
                names = list_importers()
        assert "broken" not in names
        assert "Failed to load importer plugin 'broken'" in caplog.text

    def test_module_not_found_skipped(self, caplog):
        ep = _make_entry_point("missing", None, raises=ModuleNotFoundError("nope"))
        with self._patch_entry_points([ep]):
            reset_registry()
            with caplog.at_level(logging.WARNING, logger="ctx.importers"):
                names = list_importers()
        assert "missing" not in names
        assert "Failed to load importer plugin 'missing'" in caplog.text

    def test_generic_exception_skipped(self, caplog):
        ep = _make_entry_point("crashy", None, raises=RuntimeError("boom"))
        with self._patch_entry_points([ep]):
            reset_registry()
            with caplog.at_level(logging.WARNING, logger="ctx.importers"):
                list_importers()
        assert "crashy" not in list_importers()


class TestNameCollision:
    def _patch_entry_points(self, eps):
        return patch(
            "importlib.metadata.entry_points",
            return_value=eps,
        )

    def test_plugin_overrides_builtin(self, caplog):
        """Entry-point with same name as built-in shadows it."""
        ep = _make_entry_point("liberty", _FakeImporter)
        with self._patch_entry_points([ep]):
            reset_registry()
            with caplog.at_level(logging.WARNING, logger="ctx.importers"):
                imp = get_importer("liberty")
        assert imp is not None
        assert imp.name == "fake-web"  # _FakeImporter overrides builtin
        assert "shadows existing importer" in caplog.text

    def test_two_plugins_last_wins(self, caplog):
        """When two plugins register the same name, last one wins."""

        class _AnotherFake:
            name = "another"

            def can_parse(self, path):
                return False

            def parse(self, path):
                return []

            def describe(self):
                return "another"

        ep1 = _make_entry_point("same-name", _FakeImporter)
        ep2 = _make_entry_point("same-name", _AnotherFake)
        with self._patch_entry_points([ep1, ep2]):
            reset_registry()
            with caplog.at_level(logging.WARNING, logger="ctx.importers"):
                imp = get_importer("same-name")
        assert imp is not None
        assert imp.name == "another"


    def test_same_class_no_warning(self, caplog):
        """Built-in class re-registered via entry-point should not warn."""
        from ctx.eda.parsers.liberty import LibertyParser

        ep = _make_entry_point("liberty", LibertyParser)
        with self._patch_entry_points([ep]):
            reset_registry()
            with caplog.at_level(logging.WARNING, logger="ctx.importers"):
                imp = get_importer("liberty")
        assert imp is not None
        assert "shadows existing importer" not in caplog.text


class TestAutoDetect:
    def test_auto_detect_with_plugin(self, tmp_path):
        ep = _make_entry_point("fake-web", _FakeImporter)
        with patch("importlib.metadata.entry_points", return_value=[ep]):
            reset_registry()
            f = tmp_path / "webpack.config.js"
            f.write_text("{}")
            imp = auto_detect_importer(f)
        assert imp is not None
        assert imp.name == "fake-web"
