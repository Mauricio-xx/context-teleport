"""Watch command: monitor .context-teleport/ and auto-commit/push on changes."""

from __future__ import annotations

import time
from pathlib import Path

import typer

from ctx.cli._shared import get_store
from ctx.core.store import StoreError
from ctx.sync.git_sync import GitSync, GitSyncError
from ctx.utils.output import error, info, success


def _try_push(gs: GitSync, no_push: bool) -> bool:
    """Commit and optionally push if there are changes. Returns True if changes were synced."""
    try:
        if not gs._has_changes():
            return False
        if no_push:
            result = gs.commit()
        else:
            result = gs.push()
        status = result.get("status", "")
        if status in ("committed", "pushed"):
            if no_push:
                info(f"Committed changes locally ({status})")
            else:
                success(f"Synced changes ({status})")
        return True
    except GitSyncError as e:
        error(f"Sync failed: {e}")
        return False


def _run_polling(
    gs: GitSync,
    store_dir: Path,
    debounce: float,
    interval: float,
    no_push: bool,
) -> None:
    """Polling-based watcher: check for changes every `interval` seconds."""
    info(f"Watching {store_dir} (polling every {interval}s, debounce {debounce}s)")
    last_change_time: float | None = None

    while True:
        time.sleep(interval)
        has_changes = gs._has_changes()

        if has_changes and last_change_time is None:
            last_change_time = time.monotonic()

        if has_changes and last_change_time is not None:
            elapsed = time.monotonic() - last_change_time
            if elapsed >= debounce:
                _try_push(gs, no_push)
                last_change_time = None

        if not has_changes:
            last_change_time = None


def _run_watchdog(
    gs: GitSync,
    store_dir: Path,
    debounce: float,
    no_push: bool,
) -> None:
    """Watchdog-based watcher using filesystem events."""
    import threading

    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer

    timer: threading.Timer | None = None
    lock = threading.Lock()

    class _Handler(FileSystemEventHandler):
        def on_any_event(self, event):
            nonlocal timer
            # Skip the pending conflicts file to avoid feedback loops
            if event.src_path and ".pending_conflicts" in event.src_path:
                return
            with lock:
                if timer is not None:
                    timer.cancel()
                timer = threading.Timer(debounce, lambda: _try_push(gs, no_push))
                timer.daemon = True
                timer.start()

    observer = Observer()
    observer.schedule(_Handler(), str(store_dir), recursive=True)
    observer.start()
    info(f"Watching {store_dir} (watchdog, debounce {debounce}s)")

    try:
        while observer.is_alive():
            observer.join(timeout=1.0)
    finally:
        observer.stop()
        observer.join()
        with lock:
            if timer is not None:
                timer.cancel()


def watch_command(
    debounce: float = typer.Option(5.0, "--debounce", "-d", help="Seconds to wait after last change before syncing"),
    interval: float = typer.Option(2.0, "--interval", "-i", help="Polling interval in seconds (polling mode only)"),
    no_push: bool = typer.Option(False, "--no-push", help="Only commit locally, do not push to remote"),
) -> None:
    """Watch the context store for changes and auto-sync via git.

    Uses watchdog for filesystem events if installed, falls back to polling.
    Press Ctrl+C to stop (performs a final sync before exiting).
    """
    try:
        store = get_store()
    except (StoreError, SystemExit):
        error("Context store not initialized. Run `context-teleport init` first.")
        raise typer.Exit(1)

    if not store.initialized:
        error("Context store not initialized. Run `context-teleport init` first.")
        raise typer.Exit(1)

    try:
        gs = GitSync(store.root)
    except GitSyncError as e:
        error(f"Git error: {e}")
        raise typer.Exit(1)

    # Initial sync
    _try_push(gs, no_push)

    try:
        try:
            import watchdog  # noqa: F401
            _run_watchdog(gs, store.store_dir, debounce, no_push)
        except ImportError:
            _run_polling(gs, store.store_dir, debounce, interval, no_push)
    except KeyboardInterrupt:
        info("Stopping watcher...")
        _try_push(gs, no_push)
        success("Final sync complete. Exiting.")
