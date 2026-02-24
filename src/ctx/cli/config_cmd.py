"""Config subcommands: get, set, list for global ctx settings."""

from __future__ import annotations

from typing import Optional

import typer

from ctx.cli._shared import FORMAT_OPTION
from ctx.utils.config import load_global_config, save_global_config
from ctx.utils.output import error, info, output, success

config_app = typer.Typer(no_args_is_help=True)

_VALID_KEYS = {
    "default_strategy": {"ours", "theirs", "interactive", "agent"},
    "default_scope": {"public", "private", "ephemeral"},
}


@config_app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Configuration key"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Get a configuration value."""
    if key not in _VALID_KEYS:
        error(f"Unknown key: {key}. Valid keys: {', '.join(sorted(_VALID_KEYS))}")
        raise typer.Exit(1)

    config = load_global_config()
    value = config.get(key)
    if value is None:
        if fmt == "json":
            output({"key": key, "value": None}, fmt="json")
        else:
            info(f"{key}: (not set)")
    else:
        if fmt == "json":
            output({"key": key, "value": value}, fmt="json")
        else:
            info(f"{key}: {value}")


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key"),
    value: str = typer.Argument(..., help="Value to set"),
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """Set a configuration value."""
    if key not in _VALID_KEYS:
        error(f"Unknown key: {key}. Valid keys: {', '.join(sorted(_VALID_KEYS))}")
        raise typer.Exit(1)

    valid_values = _VALID_KEYS[key]
    if value not in valid_values:
        error(f"Invalid value for {key}: {value}. Valid values: {', '.join(sorted(valid_values))}")
        raise typer.Exit(1)

    config = load_global_config()
    config[key] = value
    save_global_config(config)

    if fmt == "json":
        output({"key": key, "value": value}, fmt="json")
    else:
        success(f"{key} = {value}")


@config_app.command("list")
def config_list(
    fmt: Optional[str] = FORMAT_OPTION,
) -> None:
    """List all configuration values."""
    config = load_global_config()
    if fmt == "json":
        output(config, fmt="json")
    elif config:
        for k, v in sorted(config.items()):
            info(f"{k}: {v}")
    else:
        info("No configuration set")
