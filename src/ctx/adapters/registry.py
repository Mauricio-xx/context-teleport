"""Adapter discovery and registration."""

from __future__ import annotations

from ctx.adapters.base import AdapterProtocol
from ctx.adapters.claude_code import ClaudeCodeAdapter
from ctx.adapters.codex import CodexAdapter
from ctx.adapters.cursor import CursorAdapter
from ctx.adapters.gemini import GeminiAdapter
from ctx.adapters.opencode import OpenCodeAdapter
from ctx.core.store import ContextStore


_ADAPTER_CLASSES = {
    "claude_code": ClaudeCodeAdapter,
    "opencode": OpenCodeAdapter,
    "codex": CodexAdapter,
    "gemini": GeminiAdapter,
    "cursor": CursorAdapter,
}


def get_adapter(name: str, store: ContextStore) -> AdapterProtocol | None:
    """Get an adapter instance by name."""
    cls = _ADAPTER_CLASSES.get(name)
    if cls is None:
        return None
    return cls(store)


def list_adapters() -> list[str]:
    return list(_ADAPTER_CLASSES.keys())


def detect_adapters(store: ContextStore) -> dict[str, bool]:
    """Check which adapters are available."""
    result = {}
    for name, cls in _ADAPTER_CLASSES.items():
        adapter = cls(store)
        result[name] = adapter.detect()
    return result
