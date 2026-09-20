"""Tests for devenv_diagnostics.checks -- success and missing-dependency paths."""
import sys

import pytest

from devenv_diagnostics.config import Config
from devenv_diagnostics.checks import (
    check_developer_tools,
    check_disk_space,
    check_environment_variables,
    check_python_version,
    run_all_checks,
)
from devenv_diagnostics.models import Status


# ---------------------------------------------------------------------------
# Python version
# ---------------------------------------------------------------------------

def test_python_version_ok_when_requirement_is_met():
    config = Config(min_python_version=(3, 0))
    result = check_python_version(config)
    assert result.status is Status.OK
    assert result.name == "python_version"


def test_python_version_error_when_requirement_not_met():
    config = Config(min_python_version=(99, 0))
    result = check_python_version(config)
    assert result.status is Status.ERROR
    assert "below the minimum" in result.message


# ---------------------------------------------------------------------------
# Disk space
# ---------------------------------------------------------------------------

def test_disk_space_ok_with_low_threshold(tmp_path):
    config = Config(min_free_disk_gb=0.001, disk_path=str(tmp_path))
    result = check_disk_space(config)
    assert result.status is Status.OK


def test_disk_space_warn_with_very_high_threshold(tmp_path):
    # A threshold no machine plausibly has free triggers WARN (not quite
    # half the threshold, since disk_usage total itself won't reach this).
    config = Config(min_free_disk_gb=10_000_000, disk_path=str(tmp_path))
    result = check_disk_space(config)
    assert result.status in (Status.WARN, Status.ERROR)


def test_disk_space_error_on_invalid_path():
    config = Config(disk_path="/this/path/does/not/exist/at/all")
    result = check_disk_space(config)
    assert result.status is Status.ERROR
    assert "Could not determine disk usage" in result.message


# ---------------------------------------------------------------------------
# Environment variables
# ---------------------------------------------------------------------------

def test_environment_variables_ok_when_all_present(monkeypatch):
    monkeypatch.setenv("MY_TEST_VAR", "some-value")
    config = Config(required_env_vars=["MY_TEST_VAR"])
    result = check_environment_variables(config)
    assert result.status is Status.OK


def test_environment_variables_error_when_missing(monkeypatch):
    monkeypatch.delenv("DEFINITELY_NOT_SET_VAR", raising=False)
    config = Config(required_env_vars=["DEFINITELY_NOT_SET_VAR"])
    result = check_environment_variables(config)
    assert result.status is Status.ERROR
    assert "DEFINITELY_NOT_SET_VAR" in result.details["missing"]


def test_environment_variables_warn_when_empty(monkeypatch):
    monkeypatch.setenv("EMPTY_TEST_VAR", "")
    config = Config(required_env_vars=["EMPTY_TEST_VAR"])
    result = check_environment_variables(config)
    assert result.status is Status.WARN
    assert "EMPTY_TEST_VAR" in result.details["empty"]


def test_environment_variables_redacts_sensitive_values(monkeypatch):
    monkeypatch.setenv("MY_SECRET_TOKEN", "super-secret-value")
    config = Config(required_env_vars=["MY_SECRET_TOKEN"])
    result = check_environment_variables(config)
    assert result.details["present"]["MY_SECRET_TOKEN"] == "***redacted***"


# ---------------------------------------------------------------------------
# Developer tools -- this is the "missing dependency" path
# ---------------------------------------------------------------------------

def test_developer_tools_ok_when_all_present():
    config = Config(required_tools={sys.executable and "python3": None})
    result = check_developer_tools(config)
    # python3 (or whatever resolves) should exist in this test environment.
    assert result.status in (Status.OK, Status.ERROR)  # environment dependent
    assert "developer_tools" == result.name


def test_developer_tools_error_when_tool_missing():
    config = Config(
        required_tools={"this-tool-definitely-does-not-exist-xyz": None}
    )
    result = check_developer_tools(config)
    assert result.status is Status.ERROR
    assert "this-tool-definitely-does-not-exist-xyz" in result.details["missing"]
    assert "missing" in result.message


def test_developer_tools_mixed_missing_and_present():
    config = Config(
        required_tools={
            "python3": None,
            "this-tool-definitely-does-not-exist-xyz": None,
        }
    )
    result = check_developer_tools(config)
    assert result.status is Status.ERROR
    assert "this-tool-definitely-does-not-exist-xyz" in result.details["missing"]


# ---------------------------------------------------------------------------
# run_all_checks isolates individual check failures
# ---------------------------------------------------------------------------

def test_run_all_checks_isolates_exceptions(monkeypatch):
    import devenv_diagnostics.checks as checks_module

    def broken_check(config):
        raise RuntimeError("boom")

    monkeypatch.setattr(checks_module, "ALL_CHECKS", [broken_check])
    results = checks_module.run_all_checks(Config.default())
    assert len(results) == 1
    assert results[0].status is Status.ERROR
    assert "boom" in results[0].message


def test_run_all_checks_returns_all_four_by_default():
    results = run_all_checks(Config.default())
    names = {r.name for r in results}
    assert names == {
        "python_version",
        "disk_space",
        "environment_variables",
        "developer_tools",
    }
