# Adding EDA Parsers

How to implement a new EDA artifact parser for Context Teleport.

## Overview

EDA parsers are import-only: they read EDA-specific file formats and produce structured knowledge entries. Each parser implements the `EdaImporter` protocol.

## Step 1: Implement the protocol

Create `src/ctx/eda/parsers/newformat.py`:

```python
"""Parser for NewFormat EDA artifacts."""

from __future__ import annotations

from pathlib import Path

from ctx.eda.parsers.base import EdaImporter, ImportItem


class NewFormatParser:
    """Parse NewFormat report files."""

    name = "newformat"

    def can_parse(self, path: Path) -> bool:
        """Check if this parser handles the given file."""
        # Check file extension, name pattern, or content markers
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

## Step 2: Register in the parser registry

Edit `src/ctx/eda/parsers/__init__.py`:

```python
from ctx.eda.parsers.newformat import NewFormatParser

ALL_PARSERS = [
    LibreLaneConfigParser(),
    LibreLaneMetricsParser(),
    MagicDrcParser(),
    NetgenLvsParser(),
    OrfsConfigParser(),
    LibertyParser(),
    NewFormatParser(),  # Add here
]
```

The order matters for auto-detection: parsers are tried in order, and the first one where `can_parse()` returns `True` is used.

## Step 3: Write tests

Create `tests/eda/parsers/test_newformat.py`:

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

## Checklist

- [ ] Implement `can_parse()`, `parse()`, and `describe()`
- [ ] `name` attribute set to a descriptive slug
- [ ] `can_parse()` checks extension, then filename, optionally content
- [ ] `parse()` returns `ImportItem` objects with type `"knowledge"`
- [ ] Key follows `<format>-summary-<design>` convention
- [ ] Content is structured markdown
- [ ] Parser registered in `__init__.py`
- [ ] Tests cover: can_parse (positive and negative), parse output, key naming
- [ ] Handles malformed input gracefully
