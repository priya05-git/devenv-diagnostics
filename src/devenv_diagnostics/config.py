"""Configuration loading and validation.

The tool works with sensible defaults out of the box, but a JSON config
file can be supplied via --config to customize thresholds and required
tools. This module is responsible for turning that file into a validated
in-memory Config object, and for raising a single, well-defined
ConfigError whenever the file is missing, not valid JSON, or valid JSON
that doesn't match the expected schema.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class ConfigError(Exception):
    """Raised for any problem loading or validating a config file.

    Kept as a single exception type (rather than one per failure mode) so
    the CLI can catch it in one place and map it to EXIT_CONFIG_ERROR,
    while `str(err)` still carries a specific, actionable message.
    """


DEFAULT_MIN_PYTHON_VERSION = (3, 9)
DEFAULT_MIN_FREE_DISK_GB = 5.0
DEFAULT_REQUIRED_ENV_VARS: List[str] = ["PATH", "HOME"]
DEFAULT_REQUIRED_TOOLS: Dict[str, Optional[str]] = {
    "git": None,
    "python3": None,
}


@dataclass
class Config:
    min_python_version: tuple = DEFAULT_MIN_PYTHON_VERSION
    min_free_disk_gb: float = DEFAULT_MIN_FREE_DISK_GB
    required_env_vars: List[str] = field(
        default_factory=lambda: list(DEFAULT_REQUIRED_ENV_VARS)
    )
    required_tools: Dict[str, Optional[str]] = field(
        default_factory=lambda: dict(DEFAULT_REQUIRED_TOOLS)
    )
    disk_path: str = "."
    source: Optional[str] = None

    @classmethod
    def default(cls) -> "Config":
        return cls()


def load_config(path: Optional[str]) -> Config:
    """Load a Config from a JSON file, or return defaults if path is None.

    Raises ConfigError for:
      - a path that does not exist / is not a file
      - a file that is not valid JSON (malformed configuration)
      - JSON that does not match the expected schema (wrong types, etc.)
    """
    if path is None:
        return Config.default()

    config_path = Path(path)
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {path}")
    if not config_path.is_file():
        raise ConfigError(f"Config path is not a file: {path}")

    raw_text = config_path.read_text(encoding="utf-8")
    try:
        raw: Any = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Config file is not valid JSON ({path}): {exc.msg} "
            f"at line {exc.lineno}, column {exc.colno}"
        ) from exc

    return _validate_and_build(raw, source=path)


def _validate_and_build(raw: Any, source: str) -> Config:
    if not isinstance(raw, dict):
        raise ConfigError(
            f"Config file must contain a JSON object at the top level, "
            f"got {type(raw).__name__}"
        )

    cfg = Config.default()
    cfg.source = source

    if "min_python_version" in raw:
        value = raw["min_python_version"]
        if (
            not isinstance(value, list)
            or len(value) != 2
            or not all(isinstance(v, int) for v in value)
        ):
            raise ConfigError(
                "min_python_version must be a two-element list of integers, "
                f"e.g. [3, 9] (got {value!r})"
            )
        cfg.min_python_version = tuple(value)

    if "min_free_disk_gb" in raw:
        value = raw["min_free_disk_gb"]
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise ConfigError(
                f"min_free_disk_gb must be a non-negative number (got {value!r})"
            )
        cfg.min_free_disk_gb = float(value)

    if "required_env_vars" in raw:
        value = raw["required_env_vars"]
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ConfigError(
                f"required_env_vars must be a list of strings (got {value!r})"
            )
        cfg.required_env_vars = value

    if "required_tools" in raw:
        value = raw["required_tools"]
        if not isinstance(value, dict):
            raise ConfigError(
                f"required_tools must be an object mapping tool name -> "
                f"minimum version (or null) (got {value!r})"
            )
        for tool_name, min_version in value.items():
            if not isinstance(tool_name, str):
                raise ConfigError("required_tools keys must be strings")
            if min_version is not None and not isinstance(min_version, str):
                raise ConfigError(
                    f"required_tools['{tool_name}'] must be a string version "
                    f"or null (got {min_version!r})"
                )
        cfg.required_tools = value

    if "disk_path" in raw:
        value = raw["disk_path"]
        if not isinstance(value, str) or not value:
            raise ConfigError(f"disk_path must be a non-empty string (got {value!r})")
        cfg.disk_path = value

    return cfg
