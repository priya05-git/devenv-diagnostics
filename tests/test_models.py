"""Tests for devenv_diagnostics.models -- report aggregation logic."""
from devenv_diagnostics.models import (
    EXIT_ERROR,
    EXIT_OK,
    EXIT_WARN,
    CheckResult,
    Report,
    Status,
)


def test_report_overall_status_ok_when_all_ok():
    report = Report(checks=[CheckResult("a", Status.OK, "fine")])
    assert report.overall_status is Status.OK
    assert report.exit_code == EXIT_OK


def test_report_overall_status_warn_beats_ok():
    report = Report(
        checks=[CheckResult("a", Status.OK, "fine"), CheckResult("b", Status.WARN, "meh")]
    )
    assert report.overall_status is Status.WARN
    assert report.exit_code == EXIT_WARN


def test_report_overall_status_error_beats_warn_and_ok():
    report = Report(
        checks=[
            CheckResult("a", Status.OK, "fine"),
            CheckResult("b", Status.WARN, "meh"),
            CheckResult("c", Status.ERROR, "bad"),
        ]
    )
    assert report.overall_status is Status.ERROR
    assert report.exit_code == EXIT_ERROR


def test_report_empty_checks_is_ok():
    report = Report(checks=[])
    assert report.overall_status is Status.OK


def test_report_to_dict_summary_counts():
    report = Report(
        checks=[
            CheckResult("a", Status.OK, "fine"),
            CheckResult("b", Status.OK, "fine"),
            CheckResult("c", Status.WARN, "meh"),
            CheckResult("d", Status.ERROR, "bad"),
        ]
    )
    summary = report.to_dict()["summary"]
    assert summary == {"total": 4, "ok": 2, "warn": 1, "error": 1}
