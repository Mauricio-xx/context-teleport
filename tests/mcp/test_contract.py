"""Contract tests: verify MCP tool/resource counts match source and docs."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests.mcp.conftest import EXPECTED_RESOURCE_COUNT, EXPECTED_TOOL_COUNT

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SERVER_PY = _PROJECT_ROOT / "src" / "ctx" / "mcp" / "server.py"


def _count_decorators(source: str, pattern: str) -> int:
    """Count occurrences of a decorator pattern in source code."""
    return len(re.findall(pattern, source))


class TestMCPContract:
    @pytest.fixture(autouse=True)
    def _load_source(self):
        self.source = _SERVER_PY.read_text()

    def test_tool_count_matches_source(self):
        """EXPECTED_TOOL_COUNT must match the number of @mcp.tool() decorators."""
        actual = _count_decorators(self.source, r"@mcp\.tool\(\)")
        assert actual == EXPECTED_TOOL_COUNT, (
            f"Source has {actual} @mcp.tool() decorators but "
            f"EXPECTED_TOOL_COUNT is {EXPECTED_TOOL_COUNT}"
        )

    def test_resource_count_matches_source(self):
        """EXPECTED_RESOURCE_COUNT must match the number of @mcp.resource( decorators."""
        actual = _count_decorators(self.source, r"@mcp\.resource\(")
        assert actual == EXPECTED_RESOURCE_COUNT, (
            f"Source has {actual} @mcp.resource( decorators but "
            f"EXPECTED_RESOURCE_COUNT is {EXPECTED_RESOURCE_COUNT}"
        )

    @pytest.mark.parametrize(
        "doc_path,pattern",
        [
            ("README.md", r"(\d+) tools,\s*(\d+) resources"),
            ("docs/index.md", r"(\d+) tools,\s*(\d+) resources"),
            ("docs/reference/mcp-tools.md", r"\*\*(\d+) MCP tools\*\*"),
            ("docs/reference/mcp-resources.md", r"\*\*(\d+) MCP resources\*\*"),
        ],
        ids=["README", "docs-index", "mcp-tools-doc", "mcp-resources-doc"],
    )
    def test_doc_counts_match(self, doc_path, pattern):
        """Documentation counts must match EXPECTED constants."""
        full_path = _PROJECT_ROOT / doc_path
        content = full_path.read_text()
        match = re.search(pattern, content)
        assert match, f"Pattern {pattern!r} not found in {doc_path}"

        if match.lastindex == 2:
            # README/index pattern: captures both tools and resources
            tools = int(match.group(1))
            resources = int(match.group(2))
            assert tools == EXPECTED_TOOL_COUNT, (
                f"{doc_path} says {tools} tools but expected {EXPECTED_TOOL_COUNT}"
            )
            assert resources == EXPECTED_RESOURCE_COUNT, (
                f"{doc_path} says {resources} resources but expected {EXPECTED_RESOURCE_COUNT}"
            )
        elif "tools" in doc_path:
            count = int(match.group(1))
            assert count == EXPECTED_TOOL_COUNT, (
                f"{doc_path} says {count} tools but expected {EXPECTED_TOOL_COUNT}"
            )
        elif "resources" in doc_path:
            count = int(match.group(1))
            assert count == EXPECTED_RESOURCE_COUNT, (
                f"{doc_path} says {count} resources but expected {EXPECTED_RESOURCE_COUNT}"
            )
