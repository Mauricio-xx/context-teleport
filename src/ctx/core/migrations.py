"""Bundle versioning and migration framework.

Provides a registry for schema migrations with decorator-based registration
and BFS path finding for multi-step migrations.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Callable

SCHEMA_VERSION = "0.2.0"

MigrationFn = Callable[[dict[str, Any]], dict[str, Any]]

_registry: dict[tuple[str, str], MigrationFn] = {}


def register_migration(from_version: str, to_version: str):
    """Decorator to register a migration function between two schema versions.

    Usage:
        @register_migration("0.1.0", "0.2.0")
        def migrate_01_to_02(bundle_data: dict) -> dict:
            # transform and return
            ...
    """
    def decorator(fn: MigrationFn) -> MigrationFn:
        _registry[(from_version, to_version)] = fn
        return fn
    return decorator


def get_migration_path(from_version: str, to_version: str) -> list[str] | None:
    """Find the shortest migration path between two versions using BFS.

    Returns the version sequence (including start and end), or None if no path exists.
    """
    if from_version == to_version:
        return [from_version]

    # Build adjacency from registry
    adjacency: dict[str, list[str]] = {}
    for (src, dst) in _registry:
        adjacency.setdefault(src, []).append(dst)

    # BFS
    queue: deque[list[str]] = deque([[from_version]])
    visited = {from_version}

    while queue:
        path = queue.popleft()
        current = path[-1]

        for neighbor in adjacency.get(current, []):
            if neighbor == to_version:
                return path + [neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(path + [neighbor])

    return None


def migrate_bundle(bundle_data: dict[str, Any], target_version: str | None = None) -> dict[str, Any]:
    """Migrate bundle data to the target version (defaults to current SCHEMA_VERSION).

    Raises ValueError if no migration path exists.
    """
    target = target_version or SCHEMA_VERSION

    manifest = bundle_data.get("manifest", {})
    current_version = manifest.get("schema_version", "0.1.0")

    if current_version == target:
        return bundle_data

    path = get_migration_path(current_version, target)
    if path is None:
        raise ValueError(
            f"No migration path from {current_version} to {target}. "
            f"Bundle may be from an incompatible version."
        )

    result = bundle_data
    for i in range(len(path) - 1):
        step = (path[i], path[i + 1])
        fn = _registry[step]
        result = fn(result)

    # Update manifest version
    if "manifest" in result:
        result["manifest"]["schema_version"] = target

    return result


@register_migration("0.1.0", "0.2.0")
def migrate_010_to_020(bundle_data: dict[str, Any]) -> dict[str, Any]:
    """Migrate 0.1.0 -> 0.2.0: add scope support.

    No data transformation needed. Scope metadata (.scope.json) is created
    lazily when entries are scoped. The schema version bump signals that
    the bundle is scope-aware.
    """
    return bundle_data


def check_version_compatible(bundle_version: str) -> bool:
    """Check if a bundle version can be migrated to the current schema version.

    Returns True if the version matches current or a migration path exists.
    """
    if bundle_version == SCHEMA_VERSION:
        return True
    return get_migration_path(bundle_version, SCHEMA_VERSION) is not None
