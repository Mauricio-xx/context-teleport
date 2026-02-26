"""Test that __version__ stays in sync with pyproject.toml."""

from __future__ import annotations

from pathlib import Path

import ctx


def test_version_matches_pyproject():
    """ctx.__version__ must match the version in pyproject.toml."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    for line in pyproject.read_text().splitlines():
        if line.startswith("version = "):
            toml_version = line.split('"')[1]
            break
    else:
        raise AssertionError("Could not find version in pyproject.toml")

    assert ctx.__version__ == toml_version, (
        f"Version mismatch: ctx.__version__={ctx.__version__!r} vs pyproject.toml={toml_version!r}"
    )
