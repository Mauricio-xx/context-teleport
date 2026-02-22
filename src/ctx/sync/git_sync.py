"""Git-backed sync: push, pull, merge, log, diff."""

from __future__ import annotations

import re
from pathlib import Path

import git

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

    def pull(self) -> dict:
        """Pull remote context and validate."""
        if not self.repo.remotes:
            return {"status": "no_remote", "error": "No remote configured"}

        try:
            origin = self.repo.remotes.origin
            info = origin.pull()
            # Check if anything was updated
            if info and info[0].flags & info[0].FAST_FORWARD:
                return {"status": "pulled"}
            return {"status": "up_to_date"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

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
