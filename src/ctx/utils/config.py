"""Global and project configuration."""

from __future__ import annotations

import json
from pathlib import Path


def global_config_dir() -> Path:
    config = Path.home() / ".config" / "ctx"
    config.mkdir(parents=True, exist_ok=True)
    return config


def load_global_config() -> dict:
    path = global_config_dir() / "config.json"
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_global_config(config: dict) -> None:
    path = global_config_dir() / "config.json"
    path.write_text(json.dumps(config, indent=2))
