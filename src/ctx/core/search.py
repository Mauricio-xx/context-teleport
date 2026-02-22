"""Full-text search across knowledge files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SearchResult:
    file: str
    key: str
    line_number: int
    line: str
    score: float


def search_files(
    root: Path, query: str, file_pattern: str = "*.md"
) -> list[SearchResult]:
    """Search markdown files for a query string. Returns ranked results."""
    results: list[SearchResult] = []
    query_lower = query.lower()
    terms = query_lower.split()

    for path in sorted(root.rglob(file_pattern)):
        rel = str(path.relative_to(root))
        key = path.stem
        text = path.read_text()
        lines = text.split("\n")

        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            # Check if any term matches
            matched_terms = sum(1 for t in terms if t in line_lower)
            if matched_terms == 0:
                continue

            # Score: ratio of matched terms, boosted for headers
            score = matched_terms / len(terms)
            if line.strip().startswith("#"):
                score *= 1.5
            # Boost exact phrase match
            if query_lower in line_lower:
                score *= 2.0

            results.append(
                SearchResult(
                    file=rel,
                    key=key,
                    line_number=i,
                    line=line.strip(),
                    score=score,
                )
            )

    results.sort(key=lambda r: r.score, reverse=True)
    return results
