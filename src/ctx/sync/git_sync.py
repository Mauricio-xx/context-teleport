"""Git-backed sync: push, pull, merge, log, diff, conflict detection."""

from __future__ import annotations

import re
from pathlib import Path

import git

from ctx.core.conflicts import ConflictEntry, ConflictReport, Strategy, resolve_conflicts
from ctx.utils.paths import STORE_DIR


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
            else:
                other_changes.add(rel.split("/")[0])

        if changed_knowledge:
            parts.append(f"update {', '.join(sorted(changed_knowledge))} knowledge")
        if changed_decisions:
            parts.append(f"add decision {', '.join(sorted(changed_decisions))}")
        if other_changes:
            parts.append(f"update {', '.join(sorted(other_changes))}")

        if parts:
            return "ctx: " + ", ".join(parts)
        return "ctx: update context"

    def push(self, message: str | None = None) -> dict:
        """Stage .context-teleport/ changes, commit, and push."""
        if not self._has_changes():
            return {"status": "nothing_to_push"}

        # Stage all context files
        self.repo.index.add([STORE_DIR])
        # Also add any untracked files in the store
        untracked = [
            f for f in self.repo.untracked_files if f.startswith(STORE_DIR + "/")
        ]
        if untracked:
            self.repo.index.add(untracked)

        commit_msg = message or self._auto_message()
        self.repo.index.commit(commit_msg)

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
        try:
            self.repo.git.merge(remote_ref)
            return {"status": "pulled", "commits": len(behind)}
        except git.GitCommandError:
            pass

        # Merge failed -- detect conflicts
        report = self._build_conflict_report()
        self._pending_report = report

        if strategy in (Strategy.interactive, Strategy.agent):
            # Abort the merge so the user can resolve manually
            self.repo.git.merge("--abort")
            return {
                "status": "conflicts",
                "report": report.to_dict(),
            }

        # Auto-resolve with strategy
        resolutions = resolve_conflicts(report, strategy)
        for file_path, content in resolutions:
            abs_path = self.root / file_path
            abs_path.write_text(content)
            self.repo.index.add([file_path])

        if report.has_conflicts:
            # Some couldn't be resolved
            self.repo.git.merge("--abort")
            return {
                "status": "conflicts",
                "report": report.to_dict(),
            }

        # All resolved -- complete the merge
        self.repo.index.commit(f"ctx: merge {remote_ref} (strategy: {strategy.value})")
        self._pending_report = None
        return {
            "status": "merged",
            "strategy": strategy.value,
            "resolved": len(resolutions),
        }

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

        return {
            "status": "merged",
            "strategy": "interactive",
            "resolved": len(resolutions),
            "skipped": skipped,
        }

    def merge_status(self) -> dict:
        """Return the current conflict report, if any."""
        if self._pending_report is None:
            return {"status": "clean"}
        return {"status": "conflicts", "report": self._pending_report.to_dict()}

    def resolve(self, file_path: str, content: str) -> dict:
        """Resolve a single conflict by providing final content."""
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
