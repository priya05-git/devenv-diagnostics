"""Rendering a Report as JSON or as a human-readable text report."""
from __future__ import annotations

import json

from .models import Report, Status

_ICONS = {
    Status.OK: "[OK]   ",
    Status.WARN: "[WARN] ",
    Status.ERROR: "[ERROR]",
}


def render_json(report: Report) -> str:
    """Render the report as deterministic, pretty-printed JSON."""
    return json.dumps(report.to_dict(), indent=2, sort_keys=False)


def render_text(report: Report) -> str:
    """Render the report as a human-readable plain-text summary."""
    lines = []
    lines.append("=" * 60)
    lines.append("  Developer Environment Diagnostics Report")
    lines.append("=" * 60)
    lines.append(f"Generated at : {report.generated_at}")
    lines.append(f"Hostname     : {report.hostname}")
    lines.append(f"Tool version : {report.tool_version}")
    if report.config_source:
        lines.append(f"Config file  : {report.config_source}")
    else:
        lines.append("Config file  : (defaults)")
    lines.append("-" * 60)

    for check in report.checks:
        icon = _ICONS.get(check.status, check.status.value)
        lines.append(f"{icon} {check.name}: {check.message}")

    lines.append("-" * 60)
    summary = report.to_dict()["summary"]
    lines.append(
        f"Summary: {summary['total']} checks -- "
        f"{summary['ok']} ok, {summary['warn']} warn, {summary['error']} error"
    )
    lines.append(f"Overall status: {report.overall_status.value}")
    lines.append(f"Exit code: {report.exit_code}")
    lines.append("=" * 60)
    return "\n".join(lines)
