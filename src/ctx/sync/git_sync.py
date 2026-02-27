"""Git-backed sync: push, pull, merge, log, diff, conflict detection."""

from __future__ import annotations

import re
from pathlib import Path

import git

from ctx.core.conflicts import ConflictEntry, ConflictReport, Strategy, resolve_conflicts
from ctx.core.merge_sections import merge_markdown_sections
from ctx.core.scope import ScopeMap
from ctx.utils.paths import STORE_DIR

_PENDING_CONFLICTS_FILE = ".pending_conflicts.json"


class GitSyncError(Exception):
    pass


class GitSync:
    """Git operations scoped to the .context-teleport/ directory."""

    def __init__(self, project_root: Path) -> None:
        self.root = project_root.resolve()
        self.store_dir = self.root / STORE_DIR
        try:
            self.repo = git.Repo(self.root)
        except git.InvalidGitRepositoryError:
            raise GitSyncError(f"Not a git repository: {self.root}")

    # -- Conflict persistence (disk-backed for stateless MCP) --

    def _pending_path(self) -> Path:
        return self.store_dir / _PENDING_CONFLICTS_FILE

    def save_pending_report(self, report: ConflictReport) -> None:
        """Persist conflict report to disk."""
        self._pending_path().write_text(report.to_json())

    def load_pending_report(self) -> ConflictReport | None:
        """Load conflict report from disk, or None if no pending conflicts."""
        path = self._pending_path()
        if not path.is_file():
            return None
        try:
            return ConflictReport.from_json(path.read_text())
        except (ValueError, KeyError):
            return None

    def clear_pending_report(self) -> None:
        """Remove the pending conflicts file."""
        path = self._pending_path()
        if path.is_file():
            path.unlink()

    def has_pending_conflicts(self) -> bool:
        """Check if there are pending conflicts on disk."""
        return self._pending_path().is_file()

    def _has_changes(self) -> bool:
        """Check if there are uncommitted changes in the store directory."""
        # Check for untracked files
        untracked = [
            f for f in self.repo.untracked_files if f.startswith(STORE_DIR + "/")
        ]
        if untracked:
            return True
        # Check for modified/staged
        diff_index = self.repo.index.diff(None)
        diff_staged = self.repo.index.diff("HEAD") if self.repo.head.is_valid() else []
        for d in list(diff_index) + list(diff_staged):
            path = d.a_path or d.b_path
            if path and path.startswith(STORE_DIR + "/"):
                return True
        return False

    def _auto_message(self) -> str:
        """Generate a commit message from what changed."""
        parts = []
        diff_index = self.repo.index.diff(None)
        untracked = [
            f for f in self.repo.untracked_files if f.startswith(STORE_DIR + "/")
        ]

        changed_knowledge = set()
        changed_decisions = set()
        changed_conventions = set()
        other_changes = set()

        all_paths = [d.a_path or d.b_path for d in diff_index] + untracked
        if self.repo.head.is_valid():
            staged = self.repo.index.diff("HEAD")
            all_paths += [d.a_path or d.b_path for d in staged]

        for path in all_paths:
            if not path or not path.startswith(STORE_DIR + "/"):
                continue
            rel = path[len(STORE_DIR) + 1 :]
            if rel.startswith("knowledge/decisions/"):
                match = re.match(r"(\d+)-", rel.split("/")[-1])
                if match:
                    changed_decisions.add(match.group(1))
                else:
                    changed_decisions.add(rel.split("/")[-1])
            elif rel.startswith("knowledge/"):
                changed_knowledge.add(rel.split("/")[-1].replace(".md", ""))
            elif rel.startswith("conventions/"):
                fname = rel.split("/")[-1]
                if fname.endswith(".md"):
                    changed_conventions.add(fname.replace(".md", ""))
            elif rel.startswith("activity/"):
                other_changes.add("activity")
            else:
                other_changes.add(rel.split("/")[0])

        if changed_conventions:
            parts.append(f"update {', '.join(sorted(changed_conventions))} conventions")
        if changed_knowledge:
            parts.append(f"update {', '.join(sorted(changed_knowledge))} knowledge")
        if changed_decisions:
            parts.append(f"add decision {', '.join(sorted(changed_decisions))}")
        if other_changes:
            parts.append(f"update {', '.join(sorted(other_changes))}")

        if parts:
            return "ctx: " + ", ".join(parts)
        return "ctx: update context"

    def _get_excluded_files(self) -> set[str]:
        """Return relative paths (from repo root) of non-public files to exclude."""
        excluded = set()
        knowledge_dir = self.store_dir / "knowledge"
        decisions_dir = knowledge_dir / "decisions"
        conventions_dir = self.store_dir / "conventions"

        if knowledge_dir.is_dir():
            smap = ScopeMap(knowledge_dir)
            for fname in smap.non_public_files():
                excluded.add(f"{STORE_DIR}/knowledge/{fname}")

        if decisions_dir.is_dir():
            smap = ScopeMap(decisions_dir)
            for fname in smap.non_public_files():
                excluded.add(f"{STORE_DIR}/knowledge/decisions/{fname}")

        if conventions_dir.is_dir():
            smap = ScopeMap(conventions_dir)
            for fname in smap.non_public_files():
                excluded.add(f"{STORE_DIR}/conventions/{fname}")

        return excluded

    def _get_stageable_files(self) -> list[str]:
        """Return all store files eligible for staging (excludes non-public)."""
        excluded = self._get_excluded_files()
        stageable = []

        # Walk the store directory for tracked and modified files
        for path in self.store_dir.rglob("*"):
            if path.is_dir():
                continue
            rel = str(path.relative_to(self.root))
            if rel not in excluded:
                stageable.append(rel)

        return stageable

    def commit(self, message: str | None = None) -> dict:
        """Stage .context-teleport/ changes and commit locally (never pushes)."""
        if not self._has_changes():
            return {"status": "nothing_to_commit"}

        stageable = self._get_stageable_files()
        if not stageable:
            return {"status": "nothing_to_commit"}

        commit_msg = message or self._auto_message()
        # add() makes untracked files known to git; --only ensures the
        # commit contains ONLY our files, leaving user-staged files intact.
        self.repo.index.add(stageable)
        self.repo.git.commit("-m", commit_msg, "--only", "--", *stageable)
        return {"status": "committed", "commit_message": commit_msg}

    def push(self, message: str | None = None) -> dict:
        """Stage .context-teleport/ changes, commit, and push."""
        if not self._has_changes():
            return {"status": "nothing_to_push"}

        # Stage only public files (excludes private/ephemeral)
        stageable = self._get_stageable_files()
        if not stageable:
            return {"status": "nothing_to_push"}

        commit_msg = message or self._auto_message()
        # add() makes untracked files known to git; --only ensures the
        # commit contains ONLY our files, leaving user-staged files intact.
        self.repo.index.add(stageable)
        self.repo.git.commit("-m", commit_msg, "--only", "--", *stageable)

        # Push if remote exists
        if not self.repo.remotes:
            return {"status": "committed", "commit_message": commit_msg}

        try:
            origin = self.repo.remotes.origin
            origin.push()
            return {"status": "pushed", "commit_message": commit_msg}
        except Exception as e:
            return {
                "status": "committed",
                "commit_message": commit_msg,
                "push_error": str(e),
            }

    _pending_report: ConflictReport | None = None

    def pull(self, strategy: Strategy = Strategy.ours) -> dict:
        """Pull remote context, detect conflicts, and optionally resolve them.

        Args:
            strategy: How to resolve conflicts (ours/theirs/interactive/agent)
        """
        if not self.repo.remotes:
            return {"status": "no_remote", "error": "No remote configured"}

        try:
            origin = self.repo.remotes.origin
            origin.fetch()
        except Exception as e:
            return {"status": "error", "error": str(e)}

        branch = self.repo.active_branch.name
        remote_ref = f"origin/{branch}"

        # Check if there are changes to merge
        try:
            behind = list(self.repo.iter_commits(f"{branch}..{remote_ref}"))
        except git.GitCommandError:
            return {"status": "up_to_date"}

        if not behind:
            return {"status": "up_to_date"}

        # Attempt merge
        pre_merge = self.repo.head.commit.hexsha
        try:
            self.repo.git.merge(remote_ref)
            # Validate: only store files should have been touched
            non_store = self._merge_touched_non_store_files(pre_merge)
            if non_store:
                self.repo.git.reset("--hard", pre_merge)
                return {
                    "status": "error",
                    "error": f"Pull rejected: remote changed non-store files: {', '.join(non_store)}",
                }
            return {"status": "pulled", "commits": len(behind)}
        except git.GitCommandError:
            pass

        # Merge failed -- detect conflicts
        report = self._build_conflict_report()

        # Check if conflicts include non-store files
        non_store_conflicts = [
            p for p in self.repo.index.unmerged_blobs()
            if not p.startswith(STORE_DIR + "/")
        ]
        if non_store_conflicts:
            self.repo.git.merge("--abort")
            return {
                "status": "error",
                "error": f"Pull rejected: conflicts in non-store files: {', '.join(non_store_conflicts)}",
            }

        # Try section-level auto-merge for markdown files
        self._try_section_merge(report)

        self._pending_report = report

        if not report.has_conflicts:
            # All conflicts auto-resolved via section merge
            for conflict in report.conflicts:
                if conflict.resolved:
                    abs_path = self.root / conflict.file_path
                    abs_path.write_text(conflict.resolution)
                    self.repo.git.add(conflict.file_path)
            self.repo.git.commit("-m", f"ctx: merge {remote_ref} (section auto-merge)")
            self._pending_report = None
            return {
                "status": "merged",
                "strategy": "section-auto",
                "auto_resolved": report.auto_resolved,
            }

        if strategy in (Strategy.interactive, Strategy.agent):
            # Abort the merge so the user/agent can resolve
            self.repo.git.merge("--abort")
            if strategy == Strategy.agent:
                self.save_pending_report(report)
            return {
                "status": "conflicts",
                "report": report.to_dict(),
            }

        # Auto-resolve with strategy
        resolutions = resolve_conflicts(report, strategy)
        for file_path, content in resolutions:
            abs_path = self.root / file_path
            abs_path.write_text(content)
            self.repo.git.add(file_path)

        if report.has_conflicts:
            # Some couldn't be resolved
            self.repo.git.merge("--abort")
            return {
                "status": "conflicts",
                "report": report.to_dict(),
            }

        # All resolved -- complete the merge
        self.repo.git.commit("-m", f"ctx: merge {remote_ref} (strategy: {strategy.value})")
        self._pending_report = None
        return {
            "status": "merged",
            "strategy": strategy.value,
            "resolved": len(resolutions),
        }

    def _try_section_merge(self, report: ConflictReport) -> None:
        """Try section-level merge for .md files with base content available.

        For each conflicted markdown file that has base content, attempt a
        section-level 3-way merge.  If the merge succeeds without conflicts,
        mark the ConflictEntry as resolved and track the path in
        ``report.auto_resolved``.
        """
        for conflict in report.conflicts:
            if conflict.resolved:
                continue
            if not conflict.file_path.endswith(".md"):
                continue
            if not conflict.base_content:
                continue

            result = merge_markdown_sections(
                conflict.base_content,
                conflict.ours_content,
                conflict.theirs_content,
            )
            if not result.has_conflicts:
                conflict.resolved = True
                conflict.resolution = result.content
                report.auto_resolved.append(conflict.file_path)

    def _build_conflict_report(self) -> ConflictReport:
        """Inspect git status after a failed merge to find conflicted files."""
        report = ConflictReport()
        unmerged = self.repo.index.unmerged_blobs()

        for path, blobs in unmerged.items():
            if not path.startswith(STORE_DIR + "/"):
                continue

            # blobs is a list of (stage, Blob) tuples
            # stage 1 = base, 2 = ours, 3 = theirs
            base_content = ""
            ours_content = ""
            theirs_content = ""

            for stage, blob in blobs:
                content = blob.data_stream.read().decode("utf-8", errors="replace")
                if stage == 1:
                    base_content = content
                elif stage == 2:
                    ours_content = content
                elif stage == 3:
                    theirs_content = content

            report.conflicts.append(
                ConflictEntry(
                    file_path=path,
                    ours_content=ours_content,
                    theirs_content=theirs_content,
                    base_content=base_content,
                )
            )

        return report

    def _merge_touched_non_store_files(self, pre_merge_hex: str) -> list[str]:
        """Return non-store files changed between pre_merge_hex and HEAD."""
        diff_out = self.repo.git.diff("--name-only", pre_merge_hex, "HEAD")
        if not diff_out.strip():
            return []
        return [f for f in diff_out.strip().split("\n") if not f.startswith(STORE_DIR + "/")]

    def apply_resolutions(self, resolutions: list[tuple[str, str]]) -> dict:
        """Re-merge and apply interactive resolutions.

        After an aborted merge (interactive strategy), this method replays the
        merge: fetch, attempt merge (expect failure), write resolved files,
        fall back to 'ours' for any skipped files, and commit.

        Args:
            resolutions: List of (file_path, content) from interactive_resolve.

        Returns:
            dict with status, strategy, resolved count, skipped count.
        """
        if not self.repo.remotes:
            return {"status": "error", "error": "No remote configured"}

        origin = self.repo.remotes.origin
        origin.fetch()

        branch = self.repo.active_branch.name
        remote_ref = f"origin/{branch}"

        # Attempt merge -- may succeed if remote changed since last attempt
        try:
            self.repo.git.merge(remote_ref)
            self._pending_report = None
            return {"status": "pulled"}
        except git.GitCommandError:
            pass

        # Build conflict report from the failed merge
        report = self._build_conflict_report()
        resolved_paths = {fp for fp, _ in resolutions}

        # Apply user resolutions (use git add via CLI to clear unmerged entries)
        for file_path, content in resolutions:
            abs_path = self.root / file_path
            abs_path.write_text(content)
            self.repo.git.add(file_path)

        # Apply 'ours' for skipped/unresolved files
        skipped = 0
        for conflict in report.conflicts:
            if conflict.file_path not in resolved_paths:
                abs_path = self.root / conflict.file_path
                abs_path.write_text(conflict.ours_content)
                self.repo.git.add(conflict.file_path)
                skipped += 1

        self.repo.git.commit("-m", f"ctx: merge {remote_ref} (interactive resolution)")
        self._pending_report = None
        self.clear_pending_report()

        return {
            "status": "merged",
            "strategy": "interactive",
            "resolved": len(resolutions),
            "skipped": skipped,
        }

    def merge_status(self) -> dict:
        """Return the current conflict report, if any (checks disk if not in memory)."""
        if self._pending_report is None:
            self._pending_report = self.load_pending_report()
        if self._pending_report is None:
            return {"status": "clean"}
        return {"status": "conflicts", "report": self._pending_report.to_dict()}

    def resolve(self, file_path: str, content: str) -> dict:
        """Resolve a single conflict by providing final content."""
        if self._pending_report is None:
            self._pending_report = self.load_pending_report()
        if self._pending_report is None:
            return {"status": "error", "error": "No pending conflicts"}

        from ctx.core.conflicts import resolve_single

        found = resolve_single(self._pending_report, file_path, content)
        if not found:
            return {"status": "error", "error": f"No conflict for {file_path}"}

        return {
            "status": "resolved",
            "file_path": file_path,
            "remaining": self._pending_report.unresolved_count,
        }

    def diff(self, remote: bool = False) -> dict:
        """Show context changes."""
        try:
            if remote and self.repo.remotes:
                origin = self.repo.remotes.origin
                origin.fetch()
                diff_text = self.repo.git.diff(
                    f"origin/{self.repo.active_branch.name}",
                    "--",
                    STORE_DIR,
                )
            else:
                # Show both staged and unstaged
                diff_text = self.repo.git.diff("--", STORE_DIR)
                staged = self.repo.git.diff("--cached", "--", STORE_DIR)
                if staged:
                    diff_text = f"Staged:\n{staged}\n\nUnstaged:\n{diff_text}" if diff_text else staged
            return {"diff": diff_text}
        except Exception as e:
            return {"diff": "", "error": str(e)}

    def log(self, oneline: bool = False, count: int = 10) -> dict:
        """Show context change history."""
        try:
            args = ["--", STORE_DIR]
            if oneline:
                args = ["--oneline", f"-{count}"] + args
            else:
                args = [f"-{count}"] + args
            log_text = self.repo.git.log(*args)
            return {"log": log_text}
        except Exception as e:
            return {"log": "", "error": str(e)}
