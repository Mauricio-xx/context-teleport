"""Tests for the migration framework and bundle version checking."""

from __future__ import annotations

import pytest

from ctx.core.migrations import (
    SCHEMA_VERSION,
    _registry,
    check_version_compatible,
    get_migration_path,
    migrate_bundle,
    register_migration,
)


@pytest.fixture(autouse=True)
def clean_registry():
    """Save and restore the migration registry around each test."""
    saved = dict(_registry)
    yield
    _registry.clear()
    _registry.update(saved)


class TestSchemaVersion:
    def test_version_is_string(self):
        assert isinstance(SCHEMA_VERSION, str)

    def test_version_format(self):
        parts = SCHEMA_VERSION.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


class TestRegisterMigration:
    def test_decorator_registers(self):
        @register_migration("0.1.0", "0.2.0")
        def migrate_test(data):
            return data

        assert ("0.1.0", "0.2.0") in _registry
        assert _registry[("0.1.0", "0.2.0")] is migrate_test

    def test_decorator_preserves_function(self):
        @register_migration("0.2.0", "0.3.0")
        def my_func(data):
            return data

        assert my_func({"a": 1}) == {"a": 1}


class TestMigrationPath:
    def test_same_version(self):
        path = get_migration_path("0.1.0", "0.1.0")
        assert path == ["0.1.0"]

    def test_direct_path(self):
        @register_migration("0.1.0", "0.2.0")
        def m1(data):
            return data

        path = get_migration_path("0.1.0", "0.2.0")
        assert path == ["0.1.0", "0.2.0"]

    def test_multi_step_path(self):
        @register_migration("0.1.0", "0.2.0")
        def m1(data):
            return data

        @register_migration("0.2.0", "0.3.0")
        def m2(data):
            return data

        path = get_migration_path("0.1.0", "0.3.0")
        assert path == ["0.1.0", "0.2.0", "0.3.0"]

    def test_no_path(self):
        path = get_migration_path("0.0.1", "99.99.99")
        assert path is None


class TestMigrateBundle:
    def test_same_version_noop(self):
        data = {"manifest": {"schema_version": SCHEMA_VERSION}, "knowledge": {}}
        result = migrate_bundle(data)
        assert result is data  # identity -- no transformation

    def test_applies_migration(self):
        @register_migration("0.0.9", "0.1.0")
        def upgrade(data):
            data["migrated"] = True
            return data

        data = {"manifest": {"schema_version": "0.0.9"}, "content": "old"}
        result = migrate_bundle(data, target_version="0.1.0")
        assert result["migrated"] is True
        assert result["manifest"]["schema_version"] == "0.1.0"

    def test_multi_step_migration(self):
        @register_migration("0.0.8", "0.0.9")
        def step1(data):
            data["step1"] = True
            return data

        @register_migration("0.0.9", "0.1.0")
        def step2(data):
            data["step2"] = True
            return data

        data = {"manifest": {"schema_version": "0.0.8"}}
        result = migrate_bundle(data, target_version="0.1.0")
        assert result["step1"] is True
        assert result["step2"] is True

    def test_incompatible_raises(self):
        data = {"manifest": {"schema_version": "99.0.0"}}
        with pytest.raises(ValueError, match="No migration path"):
            migrate_bundle(data)


class TestCheckVersionCompatible:
    def test_current_version(self):
        assert check_version_compatible(SCHEMA_VERSION) is True

    def test_unknown_version(self):
        assert check_version_compatible("99.0.0") is False

    def test_migrateable_version(self):
        @register_migration("0.0.9", "0.1.0")
        def m(data):
            return data

        assert check_version_compatible("0.0.9") is True


class TestScopeMigration:
    def test_current_version_is_030(self):
        assert SCHEMA_VERSION == "0.4.0"

    def test_010_to_020_migration_exists(self):
        path = get_migration_path("0.1.0", "0.2.0")
        assert path == ["0.1.0", "0.2.0"]

    def test_migrate_010_bundle(self):
        data = {
            "manifest": {"schema_version": "0.1.0"},
            "knowledge": {"arch": "Architecture notes"},
        }
        result = migrate_bundle(data, target_version="0.2.0")
        assert result["manifest"]["schema_version"] == "0.2.0"
        assert result["knowledge"]["arch"] == "Architecture notes"


class TestMultiAgentMigration:
    def test_020_to_030_migration_exists(self):
        path = get_migration_path("0.2.0", "0.3.0")
        assert path == ["0.2.0", "0.3.0"]

    def test_migrate_020_bundle(self):
        data = {
            "manifest": {"schema_version": "0.2.0"},
            "knowledge": {"arch": "Architecture notes"},
        }
        result = migrate_bundle(data, target_version="0.3.0")
        assert result["manifest"]["schema_version"] == "0.3.0"
        assert result["knowledge"]["arch"] == "Architecture notes"

    def test_full_migration_chain(self):
        """0.1.0 -> 0.2.0 -> 0.3.0 -> 0.4.0 in one call."""
        data = {
            "manifest": {"schema_version": "0.1.0"},
            "knowledge": {"stack": "Python"},
        }
        result = migrate_bundle(data)
        assert result["manifest"]["schema_version"] == "0.4.0"
        assert result["knowledge"]["stack"] == "Python"
