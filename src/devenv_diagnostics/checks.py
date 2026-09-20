"""Individual diagnostic checks.

Each check function takes a Config and returns a single CheckResult. Every
check is self-contained and catches its own errors, converting anything
unexpected into a Status.ERROR result rather than letting an exception
escape and crash the whole run -- one bad check should never take down
the rest of the report.
"""
from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from typing import Optional

from .config import Config
from .models import CheckResult, Status


def check_python_version(config: Config) -> CheckResult:
    """Verify the running Python interpreter meets the minimum version."""
    current = sys.version_info[:2]
    required = config.min_python_version
    details = {
        "current_version": platform.python_version(),
        "required_minimum": ".".join(str(p) for p in required),
        "implementation": platform.python_implementation(),
        "executable": sys.executable,
    }
    if current >= required:
        return CheckResult(
            name="python_version",
            status=Status.OK,
            message=f"Python {details['current_version']} meets the minimum "
            f"required version {details['required_minimum']}.",
            details=details,
        )
    return CheckResult(
        name="python_version",
        status=Status.ERROR,
        message=f"Python {details['current_version']} is below the minimum "
        f"required version {details['required_minimum']}.",
        details=details,
    )


def check_disk_space(config: Config) -> CheckResult:
    """Verify free disk space on config.disk_path meets the minimum."""
    try:
        usage = shutil.disk_usage(config.disk_path)
    except OSError as exc:
        return CheckResult(
            name="disk_space",
            status=Status.ERROR,
            message=f"Could not determine disk usage for "
            f"'{config.disk_path}': {exc}",
            details={"path": config.disk_path},
        )

    free_gb = usage.free / (1024**3)
    total_gb = usage.total / (1024**3)
    used_gb = usage.used / (1024**3)
    details = {
        "path": config.disk_path,
        "free_gb": round(free_gb, 2),
        "used_gb": round(used_gb, 2),
        "total_gb": round(total_gb, 2),
        "minimum_required_gb": config.min_free_disk_gb,
    }

    if free_gb >= config.min_free_disk_gb:
        return CheckResult(
            name="disk_space",
            status=Status.OK,
            message=f"{free_gb:.2f} GB free on '{config.disk_path}' "
            f"(minimum {config.min_free_disk_gb} GB).",
            details=details,
        )

    # Below half the threshold is treated as a hard error; otherwise warn.
    if free_gb < config.min_free_disk_gb / 2:
        status = Status.ERROR
    else:
        status = Status.WARN

    return CheckResult(
        name="disk_space",
        status=status,
        message=f"Only {free_gb:.2f} GB free on '{config.disk_path}', "
        f"below the minimum of {config.min_free_disk_gb} GB.",
        details=details,
    )


def check_environment_variables(config: Config) -> CheckResult:
    """Verify all configured environment variables are set and non-empty."""
    present = {}
    missing = []
    empty = []

    for var_name in config.required_env_vars:
        if var_name not in os.environ:
            missing.append(var_name)
        elif os.environ[var_name] == "":
            empty.append(var_name)
        else:
            present[var_name] = _redact(var_name, os.environ[var_name])

    details = {
        "required": config.required_env_vars,
        "present": present,
        "missing": missing,
        "empty": empty,
    }

    if not missing and not empty:
        return CheckResult(
            name="environment_variables",
            status=Status.OK,
            message=f"All {len(config.required_env_vars)} required "
            f"environment variable(s) are set.",
            details=details,
        )

    problems = missing + empty
    status = Status.ERROR if missing else Status.WARN
    return CheckResult(
        name="environment_variables",
        status=status,
        message="Environment variable issue(s): "
        + ", ".join(
            [f"{v} missing" for v in missing] + [f"{v} empty" for v in empty]
        ),
        details=details,
    )


def _redact(var_name: str, value: str) -> str:
    """Avoid printing likely-sensitive values (tokens, keys, secrets) in full."""
    sensitive_markers = ("key", "secret", "token", "password", "pass", "pwd")
    if any(marker in var_name.lower() for marker in sensitive_markers):
        return "***redacted***"
    if len(value) > 80:
        return value[:77] + "..."
    return value


def _get_tool_version(tool: str) -> Optional[str]:
    """Best-effort extraction of a version string from `tool --version`."""
    for flag in ("--version", "-v", "version"):
        try:
            proc = subprocess.run(
                [tool, flag],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        output = (proc.stdout or "") + (proc.stderr or "")
        match = re.search(r"(\d+\.\d+(?:\.\d+)?)", output)
        if match:
            return match.group(1)
        if output.strip():
            return output.strip().splitlines()[0][:60]
    return None


def _version_tuple(version: str) -> tuple:
    parts = re.findall(r"\d+", version)
    return tuple(int(p) for p in parts) if parts else (0,)


def check_developer_tools(config: Config) -> CheckResult:
    """Verify each configured developer tool is installed (and optionally
    meets a minimum version)."""
    found = {}
    missing = []
    outdated = {}

    for tool_name, min_version in config.required_tools.items():
        tool_path = shutil.which(tool_name)
        if tool_path is None:
            missing.append(tool_name)
            continue

        version = _get_tool_version(tool_name)
        found[tool_name] = {"path": tool_path, "version": version}

        if min_version and version:
            if _version_tuple(version) < _version_tuple(min_version):
                outdated[tool_name] = {"found": version, "required": min_version}

    details = {
        "required_tools": config.required_tools,
        "found": found,
        "missing": missing,
        "outdated": outdated,
    }

    if not missing and not outdated:
        return CheckResult(
            name="developer_tools",
            status=Status.OK,
            message=f"All {len(config.required_tools)} configured developer "
            f"tool(s) are installed and meet version requirements.",
            details=details,
        )

    parts = []
    if missing:
        parts.append(f"missing: {', '.join(missing)}")
    if outdated:
        outdated_desc = ", ".join(
            f"{name} ({info['found']} < {info['required']})"
            for name, info in outdated.items()
        )
        parts.append(f"outdated: {outdated_desc}")

    status = Status.ERROR if missing else Status.WARN
    return CheckResult(
        name="developer_tools",
        status=status,
        message="Developer tool issue(s) -- " + "; ".join(parts),
        details=details,
    )


# The ordered set of checks that make up a full diagnostic run.
ALL_CHECKS = [
    check_python_version,
    check_disk_space,
    check_environment_variables,
    check_developer_tools,
]


def run_all_checks(config: Config) -> list:
    """Run every registered check, isolating failures to a single ERROR result."""
    results = []
    for check_fn in ALL_CHECKS:
        try:
            results.append(check_fn(config))
        except Exception as exc:  # noqa: BLE001 - isolate unexpected failures
            results.append(
                CheckResult(
                    name=getattr(check_fn, "__name__", "unknown_check"),
                    status=Status.ERROR,
                    message=f"Check raised an unexpected exception: {exc}",
                    details={"exception_type": type(exc).__name__},
                )
            )
    return results
