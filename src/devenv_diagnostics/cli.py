"""Command-line entry point for devenv-diagnostics.

Usage:
    devenv-diag [--config PATH] [--json] [--output PATH] [--disk-path PATH] [--quiet]

Exit codes:
    0  all checks passed
    1  one or more checks produced a warning, no errors
    2  one or more checks failed (e.g. missing required dependency)
    3  the supplied --config file was missing, malformed, or invalid
    4  an unexpected internal error occurred
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional, Sequence

from . import __version__
from .checks import run_all_checks
from .config import ConfigError, load_config
from .models import EXIT_CONFIG_ERROR, EXIT_INTERNAL_ERROR, Report
from .report import render_json, render_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devenv-diag",
        description="Inspect this machine and produce a developer-environment "
        "health report.",
    )
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Path to a JSON config file overriding default thresholds "
        "(min Python version, disk space, required env vars, required tools).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON instead of the human-readable report.",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="Write the report to PATH instead of stdout.",
    )
    parser.add_argument(
        "--disk-path",
        metavar="PATH",
        default=None,
        help="Override the path used for the disk-space check "
        "(defaults to '.' or the value from --config).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suspend printing to stdout (useful with --output).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"devenv-diag {__version__}",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except ConfigError as exc:
        sys.stderr.write(f"Configuration error: {exc}\n")
        return EXIT_CONFIG_ERROR

    if args.disk_path:
        config.disk_path = args.disk_path

    try:
        checks = run_all_checks(config)
        report = Report(
            checks=checks,
            tool_version=__version__,
            config_source=config.source,
        )
    except Exception as exc:  # noqa: BLE001 - last-resort safety net
        sys.stderr.write(f"Internal error while running diagnostics: {exc}\n")
        return EXIT_INTERNAL_ERROR

    rendered = render_json(report) if args.json else render_text(report)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(rendered + "\n")
        except OSError as exc:
            sys.stderr.write(f"Could not write output to {args.output}: {exc}\n")
            return EXIT_INTERNAL_ERROR

    if not args.quiet:
        print(rendered)

    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
