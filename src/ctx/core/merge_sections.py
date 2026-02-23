"""Section-level three-way merge for markdown files."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ctx.core.merge import MergeResult


@dataclass
class Section:
    header: str  # "## Backend" or "" for preamble
    content: str  # everything until next ## or EOF


def parse_sections(text: str) -> list[Section]:
    """Split markdown by ## headers. Content before first ## is the preamble."""
    # Match lines that start with exactly ## (not ### or more)
    pattern = re.compile(r"^(## .+)$", re.MULTILINE)

    sections: list[Section] = []
    matches = list(pattern.finditer(text))

    if not matches:
        # No ## headers at all -- entire text is preamble
        return [Section(header="", content=text)]

    # Preamble: everything before the first ## header
    preamble_text = text[: matches[0].start()]
    if preamble_text or not matches:
        sections.append(Section(header="", content=preamble_text))

    for i, match in enumerate(matches):
        header = match.group(1)
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end]
        sections.append(Section(header=header, content=content))

    return sections


def _normalize_header(header: str) -> str:
    """Normalize header for comparison: strip ## prefix, lowercase, strip whitespace."""
    return re.sub(r"^#{1,6}\s*", "", header).strip().lower()


def _sections_to_dict(sections: list[Section]) -> dict[str, Section]:
    """Build a lookup from normalized header -> Section."""
    result: dict[str, Section] = {}
    for s in sections:
        key = _normalize_header(s.header) if s.header else ""
        result[key] = s
    return result


def _section_order(sections: list[Section]) -> list[str]:
    """Return list of normalized header keys preserving order."""
    return [_normalize_header(s.header) if s.header else "" for s in sections]


def merge_markdown_sections(base: str, ours: str, theirs: str) -> MergeResult:
    """Section-level 3-way merge for markdown.

    For each section (identified by ## header):
    - If only one side changed, take that change
    - If both changed to same content, take it
    - If both changed differently, mark section-level conflict
    - New sections from either side are included
    - Deleted sections: if one side deletes and other doesn't change, accept deletion.
      If one deletes and other modifies, conflict.

    Returns MergeResult with merged content and per-section conflict details.
    """
    base_sections = parse_sections(base)
    ours_sections = parse_sections(ours)
    theirs_sections = parse_sections(theirs)

    base_dict = _sections_to_dict(base_sections)
    ours_dict = _sections_to_dict(ours_sections)
    theirs_dict = _sections_to_dict(theirs_sections)

    base_keys = _section_order(base_sections)
    ours_keys = _section_order(ours_sections)
    theirs_keys = _section_order(theirs_sections)

    all_ours_keys = set(ours_keys)
    all_theirs_keys = set(theirs_keys)

    # If none of the three have ## headers, fall back to whole-file comparison
    has_headers_base = any(s.header for s in base_sections)
    has_headers_ours = any(s.header for s in ours_sections)
    has_headers_theirs = any(s.header for s in theirs_sections)

    if not has_headers_base and not has_headers_ours and not has_headers_theirs:
        # Plain text fallback: whole-file comparison
        if ours == theirs:
            return MergeResult(content=ours, has_conflicts=False)
        if ours == base:
            return MergeResult(content=theirs, has_conflicts=False)
        if theirs == base:
            return MergeResult(content=ours, has_conflicts=False)
        # Both changed differently
        return MergeResult(
            content=ours,
            has_conflicts=True,
            conflict_details=[
                f"Whole-file conflict: ours ({len(ours)} chars) vs theirs ({len(theirs)} chars)"
            ],
        )

    conflicts: list[str] = []
    merged_sections: list[Section] = []
    processed_keys: set[str] = set()

    def _content_eq(a: str, b: str) -> bool:
        """Compare section content ignoring trailing whitespace.

        Trailing blank lines shift when sections are added/removed,
        so they shouldn't count as meaningful changes.
        """
        return a.rstrip() == b.rstrip()

    # Process sections in base order first
    for key in base_keys:
        if key in processed_keys:
            continue
        processed_keys.add(key)

        base_sec = base_dict[key]
        in_ours = key in all_ours_keys
        in_theirs = key in all_theirs_keys

        if in_ours and in_theirs:
            ours_sec = ours_dict[key]
            theirs_sec = theirs_dict[key]

            ours_changed = not _content_eq(ours_sec.content, base_sec.content)
            theirs_changed = not _content_eq(theirs_sec.content, base_sec.content)

            if not ours_changed and not theirs_changed:
                # Neither changed -- use ours version (preserves ours formatting)
                merged_sections.append(
                    Section(header=ours_sec.header, content=ours_sec.content)
                )
            elif ours_changed and not theirs_changed:
                # Only ours changed
                merged_sections.append(
                    Section(header=ours_sec.header, content=ours_sec.content)
                )
            elif theirs_changed and not ours_changed:
                # Only theirs changed -- use theirs content but ours header formatting
                header = ours_sec.header if ours_sec.header else theirs_sec.header
                merged_sections.append(
                    Section(header=header, content=theirs_sec.content)
                )
            elif _content_eq(ours_sec.content, theirs_sec.content):
                # Both changed to the same thing
                merged_sections.append(
                    Section(header=ours_sec.header, content=ours_sec.content)
                )
            else:
                # Both changed differently -- conflict, default to ours
                label = base_sec.header or "preamble"
                conflicts.append(
                    f"Section '{label}': both sides modified differently"
                )
                merged_sections.append(
                    Section(header=ours_sec.header, content=ours_sec.content)
                )

        elif in_ours and not in_theirs:
            # Theirs deleted this section
            ours_sec = ours_dict[key]
            ours_changed = not _content_eq(ours_sec.content, base_sec.content)

            if ours_changed:
                # Theirs deleted, ours modified -- conflict
                label = base_sec.header or "preamble"
                conflicts.append(
                    f"Section '{label}': deleted by theirs but modified by ours"
                )
                merged_sections.append(
                    Section(header=ours_sec.header, content=ours_sec.content)
                )
            else:
                # Theirs deleted, ours unchanged -- accept deletion
                pass

        elif not in_ours and in_theirs:
            # Ours deleted this section
            theirs_sec = theirs_dict[key]
            theirs_changed = not _content_eq(theirs_sec.content, base_sec.content)

            if theirs_changed:
                # Ours deleted, theirs modified -- conflict
                label = base_sec.header or "preamble"
                conflicts.append(
                    f"Section '{label}': deleted by ours but modified by theirs"
                )
                # Include theirs version since ours deleted it
                merged_sections.append(
                    Section(header=theirs_sec.header, content=theirs_sec.content)
                )
            else:
                # Ours deleted, theirs unchanged -- accept deletion
                pass

        else:
            # Both deleted -- accept deletion
            pass

    # Append new sections from ours (not in base)
    for key in ours_keys:
        if key in processed_keys:
            continue
        processed_keys.add(key)
        ours_sec = ours_dict[key]

        if key in all_theirs_keys:
            # Both sides added a section with the same header
            theirs_sec = theirs_dict[key]
            if _content_eq(ours_sec.content, theirs_sec.content):
                # Same content, no conflict
                merged_sections.append(
                    Section(header=ours_sec.header, content=ours_sec.content)
                )
            else:
                # Different content, conflict
                label = ours_sec.header or "preamble"
                conflicts.append(
                    f"Section '{label}': added by both sides with different content"
                )
                merged_sections.append(
                    Section(header=ours_sec.header, content=ours_sec.content)
                )
        else:
            # Only ours added it
            merged_sections.append(
                Section(header=ours_sec.header, content=ours_sec.content)
            )

    # Append new sections from theirs (not in base, not already handled)
    for key in theirs_keys:
        if key in processed_keys:
            continue
        processed_keys.add(key)
        theirs_sec = theirs_dict[key]
        merged_sections.append(
            Section(header=theirs_sec.header, content=theirs_sec.content)
        )

    # Reassemble
    parts: list[str] = []
    for sec in merged_sections:
        if sec.header:
            parts.append(sec.header + sec.content)
        else:
            parts.append(sec.content)

    merged_text = "".join(parts)

    return MergeResult(
        content=merged_text,
        has_conflicts=len(conflicts) > 0,
        conflict_details=conflicts,
    )
