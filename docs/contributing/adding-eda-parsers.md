# Adding Domain Importers

How to add new artifact importers to Context Teleport -- either as built-in
EDA parsers or as third-party plugins.

## Overview

Domain importers are import-only: they read artifact files and produce
structured knowledge entries. Each importer implements the `ArtifactImporter`
protocol (or the identical `EdaImporter` protocol for EDA-specific parsers).

There are two ways to register an importer:

1. **Built-in**: add a parser class to `src/ctx/eda/parsers/` and register it
   in the `_IMPORTERS` dict (for code shipped with Context Teleport)
2. **Entry-point plugin**: ship a separate Python package that registers
   importers via the `ctx.importers` entry-point group (for third-party or
   domain-specific importers)

Both paths make the importer available through `context-teleport import artifacts`.

## Step 1: Implement the protocol

Create a new module for your importer. For built-in EDA parsers, this goes in
`src/ctx/eda/parsers/`. For third-party plugins, put it wherever your package
lives.

```python
"""Parser for NewFormat EDA artifacts."""

from __future__ import annotations

from pathlib import Path

from ctx.importers.base import ArtifactImporter, ImportItem


class NewFormatParser:
    """Parse NewFormat report files."""

    name = "newformat"

    def can_parse(self, path: Path) -> bool:
        """Check if this parser handles the given file."""
        # Check file extension first (cheapest)
        if path.suffix == ".nf":
            return True
        if path.name.endswith(".newformat.txt"):
            return True
        # Optionally check file contents for format markers
        try:
            header = path.read_text(errors="replace")[:200]
            return "NewFormat Report" in header
        except OSError:
            return False

    def parse(self, path: Path) -> list[ImportItem]:
        """Parse the file and return knowledge items."""
        text = path.read_text(errors="replace")
        items = []

        # Extract relevant information from the file
        design_name = self._extract_design_name(text, path)
        summary = self._build_summary(text)

        items.append(ImportItem(
            type="knowledge",
            key=f"newformat-summary-{design_name}",
            content=summary,
            source=str(path),
        ))

        return items

    def describe(self) -> str:
        """Human-readable description."""
        return "NewFormat EDA report files (.nf, *.newformat.txt)"

    def _extract_design_name(self, text: str, path: Path) -> str:
        """Extract design name from file content or path."""
        # Try to find design name in content
        # Fall back to filename-based extraction
        return path.stem.split(".")[0]

    def _build_summary(self, text: str) -> str:
        """Build a markdown summary from the parsed content."""
        lines = ["## NewFormat Summary", ""]
        # Parse and structure the content
        lines.append("(parsed content here)")
        return "\n".join(lines)
```

!!! note "Import path for third-party plugins"
    Third-party plugins should import from `ctx.importers.base` (which
    re-exports `ImportItem`), not from `ctx.eda.parsers.base`. The
    `ctx.importers.base` module is the stable public API for plugin authors.

## Step 2: Register the importer

### Option A: Built-in registration (for Context Teleport contributors)

Edit `src/ctx/eda/parsers/__init__.py` and add your parser to the `_IMPORTERS`
dict:

```python
from ctx.eda.parsers.newformat import NewFormatParser

_IMPORTERS: dict[str, type] = {
    "librelane-config": LibreLaneConfigParser,
    "librelane-metrics": LibreLaneMetricsParser,
    "magic-drc": MagicDrcParser,
    "netgen-lvs": NetgenLvsParser,
    "orfs-config": OrfsConfigParser,
    "liberty": LibertyParser,
    "newformat": NewFormatParser,  # Add here
}
```

The dict key is the importer name used with `--type`. Auto-detection iterates
all importers and uses the first one where `can_parse()` returns `True`.

### Option B: Entry-point registration (for third-party plugins)

Add an entry point to your package's `pyproject.toml`:

```toml
[project.entry-points."ctx.importers"]
newformat = "my_package.parsers:NewFormatParser"
```

When Context Teleport loads its plugin registry, it discovers all packages that
declare entry points in the `ctx.importers` group. The registry loads built-in
importers first, then entry-point plugins. If an entry-point name collides with
a built-in name, the entry-point version takes precedence (with a warning).

After installing your package, verify registration:

```bash
context-teleport import artifacts --list
# Should show "newformat" alongside the built-in importers
```

### Example: hypothetical web importer

A third-party package that imports web project artifacts might look like:

```toml
# pyproject.toml for "ctx-web-importers"
[project]
name = "ctx-web-importers"
version = "0.1.0"
dependencies = ["context-teleport>=0.5.5"]

[project.entry-points."ctx.importers"]
webpack-config = "ctx_web_importers.webpack:WebpackConfigParser"
lighthouse = "ctx_web_importers.lighthouse:LighthouseParser"
```

Once installed, both `webpack-config` and `lighthouse` appear in the registry
and can be used with `context-teleport import artifacts`.

## Step 3: Write tests

Create test files for your importer:

```python
import pytest
from pathlib import Path

from ctx.eda.parsers.newformat import NewFormatParser


@pytest.fixture
def parser():
    return NewFormatParser()


def test_name(parser):
    assert parser.name == "newformat"


def test_describe(parser):
    desc = parser.describe()
    assert "NewFormat" in desc


def test_can_parse_by_extension(parser, tmp_path):
    f = tmp_path / "report.nf"
    f.write_text("NewFormat Report\nsome data")
    assert parser.can_parse(f) is True


def test_can_parse_rejects_other(parser, tmp_path):
    f = tmp_path / "report.txt"
    f.write_text("unrelated content")
    assert parser.can_parse(f) is False


def test_parse_produces_items(parser, tmp_path):
    f = tmp_path / "mydesign.nf"
    f.write_text("NewFormat Report\nDesign: mydesign\nResults: PASS")
    items = parser.parse(f)
    assert len(items) >= 1
    assert items[0].type == "knowledge"
    assert "newformat-summary" in items[0].key
    assert items[0].source == str(f)


def test_parse_key_includes_design(parser, tmp_path):
    f = tmp_path / "inverter.nf"
    f.write_text("NewFormat Report\nsome data")
    items = parser.parse(f)
    assert "inverter" in items[0].key
```

## Design guidelines

### `can_parse()` should be reliable

- Check file extension first (cheapest)
- Then check filename patterns
- Optionally read a small portion of the file for format markers
- Never read the entire file in `can_parse()` -- that's what `parse()` is for
- Return `False` on any I/O error

### `parse()` should be robust

- Use `errors="replace"` when reading text to handle encoding issues
- Handle malformed or incomplete files gracefully (return partial results)
- Use the file path as fallback for design names
- Return an empty list if the file can't be meaningfully parsed

### Key naming convention

Keys should follow the pattern: `<format>-summary-<design-name>`

Examples from existing parsers:

| Parser | Key pattern |
|--------|------------|
| librelane-config | `librelane-config-<design>` |
| librelane-metrics | `librelane-metrics-<design>` |
| magic-drc | `drc-summary-<design>` |
| netgen-lvs | `lvs-summary-<design>` |
| orfs-config | `orfs-config-<design>` |
| liberty | `liberty-summary-<library>` |

### Content format

The `content` field should be structured markdown:

```markdown
## DRC Summary: inverter

**Design**: inverter
**Total violations**: 15
**Status**: FAIL

### Violations by category

| Category | Count |
|----------|-------|
| Metal spacing | 3 |
| Via enclosure | 8 |
| Density | 4 |
```

### Re-import behavior

Importing the same file twice should produce the same key, overwriting the previous entry. This allows updating context as design iterations proceed.

### Security requirements for plugins

Third-party importers must be **read-only**:

- No subprocess execution or shell commands
- No file writes outside the context store
- No network requests
- Only read the artifact file passed to `parse()`

## Third-party plugins

The `ArtifactImporter` protocol in `ctx.importers.base` is the public API for
plugin authors:

```python
from ctx.importers.base import ArtifactImporter, ImportItem
```

This module re-exports `ImportItem` from the internal EDA parsers package, so
plugin authors only need a single import source.

The plugin registry (`ctx.importers`) uses lazy loading: importers are
discovered on first access. Built-in EDA parsers are loaded from the
`_IMPORTERS` dict, then entry-point plugins from the `ctx.importers` group.
Broken plugins (import errors, missing attributes) are logged and skipped
without crashing.

Key registry functions (for testing and advanced use):

- `list_importers()` -- all registered importer names
- `get_importer(name)` -- get a specific importer by name
- `auto_detect_importer(path)` -- first importer where `can_parse()` is `True`
- `reset_registry()` -- clear the cache (useful in tests)

## Checklist

- [ ] Implement `can_parse()`, `parse()`, and `describe()`
- [ ] `name` attribute set to a descriptive slug
- [ ] `can_parse()` checks extension, then filename, optionally content
- [ ] `parse()` returns `ImportItem` objects with type `"knowledge"`
- [ ] Key follows `<format>-summary-<design>` convention
- [ ] Content is structured markdown
- [ ] Registered via `_IMPORTERS` dict (built-in) or `pyproject.toml` entry point (plugin)
- [ ] Tests cover: can_parse (positive and negative), parse output, key naming
- [ ] Handles malformed input gracefully
- [ ] Read-only: no subprocess, no writes outside store, no network
