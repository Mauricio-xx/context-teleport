"""Fixtures for importer registry tests."""

import pytest

from ctx.importers import reset_registry


@pytest.fixture(autouse=True)
def _clean_registry():
    """Reset the importer registry before and after each test."""
    reset_registry()
    yield
    reset_registry()
