"""Tests for interactive conflict resolution TUI."""

from __future__ import annotations

from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console

from ctx.cli.interactive import interactive_resolve
from ctx.core.conflicts import ConflictEntry, ConflictReport


def _make_report(*conflicts: tuple[str, str, str]) -> ConflictReport:
    """Build a ConflictReport from (path, ours, theirs) tuples."""
    report = ConflictReport()
    for path, ours, theirs in conflicts:
        report.conflicts.append(ConflictEntry(
            file_path=path,
            ours_content=ours,
            theirs_content=theirs,
            base_content="",
        ))
    return report


def _test_console() -> Console:
    return Console(file=StringIO(), force_terminal=True)


@pytest.fixture(autouse=True)
def _force_tty(monkeypatch):
    """Tests run under pytest where stdout is not a TTY. Force is_piped=False
    so interactive_resolve doesn't bail out. The explicit piped test overrides this."""
    monkeypatch.setattr("ctx.cli.interactive.is_piped", lambda: False)


class TestInteractiveResolve:
    def test_choose_ours(self):
        report = _make_report(("file.md", "ours content", "theirs content"))
        console = _test_console()

        result = interactive_resolve(report, console=console, prompt_fn=lambda *a, **kw: "o")

        assert len(result) == 1
        assert result[0] == ("file.md", "ours content")

    def test_choose_theirs(self):
        report = _make_report(("file.md", "ours content", "theirs content"))
        console = _test_console()

        result = interactive_resolve(report, console=console, prompt_fn=lambda *a, **kw: "t")

        assert len(result) == 1
        assert result[0] == ("file.md", "theirs content")

    def test_skip(self):
        report = _make_report(("file.md", "ours", "theirs"))
        console = _test_console()

        result = interactive_resolve(report, console=console, prompt_fn=lambda *a, **kw: "s")

        assert result == []

    def test_multiple_files_mixed_choices(self):
        report = _make_report(
            ("a.md", "ours-a", "theirs-a"),
            ("b.md", "ours-b", "theirs-b"),
            ("c.md", "ours-c", "theirs-c"),
        )
        console = _test_console()
        responses = iter(["o", "t", "s"])

        result = interactive_resolve(
            report,
            console=console,
            prompt_fn=lambda *a, **kw: next(responses),
        )

        assert len(result) == 2
        assert result[0] == ("a.md", "ours-a")
        assert result[1] == ("b.md", "theirs-b")

    def test_already_resolved_skipped(self):
        report = _make_report(("a.md", "ours-a", "theirs-a"), ("b.md", "ours-b", "theirs-b"))
        report.conflicts[0].resolved = True
        report.conflicts[0].resolution = "already done"

        console = _test_console()

        result = interactive_resolve(report, console=console, prompt_fn=lambda *a, **kw: "t")

        assert len(result) == 1
        assert result[0] == ("b.md", "theirs-b")

    def test_edit_choice(self):
        report = _make_report(("file.md", "original", "theirs"))
        console = _test_console()

        with patch("ctx.cli.interactive._edit_content", return_value="edited content"):
            result = interactive_resolve(
                report,
                console=console,
                prompt_fn=lambda *a, **kw: "e",
            )

        assert len(result) == 1
        assert result[0] == ("file.md", "edited content")

    def test_edit_failure_skips(self):
        report = _make_report(("file.md", "original", "theirs"))
        console = _test_console()

        with patch("ctx.cli.interactive._edit_content", return_value=None):
            result = interactive_resolve(
                report,
                console=console,
                prompt_fn=lambda *a, **kw: "e",
            )

        assert result == []

    def test_noninteractive_fallback(self, monkeypatch):
        report = _make_report(("file.md", "ours", "theirs"))
        console = _test_console()

        # Override the autouse fixture
        monkeypatch.setattr("ctx.cli.interactive.is_piped", lambda: True)
        result = interactive_resolve(report, console=console, prompt_fn=lambda *a, **kw: "o")

        assert result == []

    def test_summary_output(self):
        report = _make_report(("a.md", "ours-a", "theirs-a"), ("b.md", "ours-b", "theirs-b"))
        buf = StringIO()
        console = Console(file=buf, force_terminal=True)
        responses = iter(["o", "t"])

        interactive_resolve(
            report,
            console=console,
            prompt_fn=lambda *a, **kw: next(responses),
        )

        output_text = buf.getvalue()
        assert "Resolution Summary" in output_text
        assert "a.md" in output_text
        assert "b.md" in output_text
