"""Data structures shared across the diagnostics tool."""
from __future__ import annotations

import platform
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class Status(str, Enum):
    """Outcome of a single diagnostic check.

    Ordering matters: it is used to compute the worst-case status of a
    report (max() over a list of Status values follows this order).
    """

    OK = "OK"
    WARN = "WARN"
    ERROR = "ERROR"

    @property
    def severity(self) -> int:
        return {"OK": 0, "WARN": 1, "ERROR": 2}[self.value]

    def __lt__(self, other: "Status") -> bool:
        if not isinstance(other, Status):
            return NotImplemented
        return self.severity < other.severity


# Exit codes returned by the CLI. Kept as plain ints (not an Enum) so they
# can be used directly with sys.exit().
EXIT_OK = 0
EXIT_WARN = 1
EXIT_ERROR = 2
EXIT_CONFIG_ERROR = 3
EXIT_INTERNAL_ERROR = 4


@dataclass
class CheckResult:
    """The outcome of a single diagnostic check."""

    name: str
    status: Status
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class Report:
    """Aggregated result of a full diagnostic run."""

    checks: List[CheckResult]
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    hostname: str = field(default_factory=platform.node)
    tool_version: str = "1.0.0"
    config_source: Optional[str] = None

    @property
    def overall_status(self) -> Status:
        if not self.checks:
            return Status.OK
        return max((c.status for c in self.checks), key=lambda s: s.severity)

    @property
    def exit_code(self) -> int:
        status = self.overall_status
        if status is Status.OK:
            return EXIT_OK
        if status is Status.WARN:
            return EXIT_WARN
        return EXIT_ERROR

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": "devenv-diagnostics",
            "tool_version": self.tool_version,
            "generated_at": self.generated_at,
            "hostname": self.hostname,
            "config_source": self.config_source,
            "overall_status": self.overall_status.value,
            "exit_code": self.exit_code,
            "checks": [c.to_dict() for c in self.checks],
            "summary": {
                "total": len(self.checks),
                "ok": sum(1 for c in self.checks if c.status is Status.OK),
                "warn": sum(1 for c in self.checks if c.status is Status.WARN),
                "error": sum(1 for c in self.checks if c.status is Status.ERROR),
            },
        }
