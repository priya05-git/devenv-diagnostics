"""End-to-end tests for the CLI: exit codes and output formats."""
import json

import pytest

from devenv_diagnostics.cli import main
from devenv_diagnostics.models import EXIT_CONFIG_ERROR, EXIT_ERROR, EXIT_OK


def test_cli_success_path_exits_zero(tmp_path, capsys, monkeypatch):
    """All checks configured to trivially pass -> exit code 0."""
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "min_python_version": [3, 0],
                "min_free_disk_gb": 0.001,
                "required_env_vars": ["PATH"],
                "required_tools": {},
                "disk_path": str(tmp_path),
            }
        )
    )
    exit_code = main(["--config", str(config_file), "--json"])
    assert exit_code == EXIT_OK

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["overall_status"] == "OK"
    assert payload["exit_code"] == 0


def test_cli_missing_dependency_path_exits_two(tmp_path, capsys):
    """A required tool that doesn't exist -> ERROR status, exit code 2."""
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "min_python_version": [3, 0],
                "min_free_disk_gb": 0.001,
                "required_env_vars": [],
                "required_tools": {"this-tool-does-not-exist-anywhere": None},
                "disk_path": str(tmp_path),
            }
        )
    )
    exit_code = main(["--config", str(config_file), "--json"])
    assert exit_code == EXIT_ERROR

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    tool_check = next(c for c in payload["checks"] if c["name"] == "developer_tools")
    assert tool_check["status"] == "ERROR"
    assert "this-tool-does-not-exist-anywhere" in tool_check["details"]["missing"]


def test_cli_malformed_config_path_exits_three(tmp_path, capsys):
    """An unparsable config file -> exit code 3, no report emitted."""
    config_file = tmp_path / "bad.json"
    config_file.write_text("{not valid json,,,")

    exit_code = main(["--config", str(config_file)])
    assert exit_code == EXIT_CONFIG_ERROR

    captured = capsys.readouterr()
    assert captured.out == ""  # no report body printed on config error


def test_cli_missing_config_file_exits_three(tmp_path):
    missing = tmp_path / "nope.json"
    exit_code = main(["--config", str(missing)])
    assert exit_code == EXIT_CONFIG_ERROR


def test_cli_text_output_contains_summary(tmp_path, capsys):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "min_python_version": [3, 0],
                "min_free_disk_gb": 0.001,
                "required_env_vars": [],
                "required_tools": {},
                "disk_path": str(tmp_path),
            }
        )
    )
    exit_code = main(["--config", str(config_file)])
    assert exit_code == EXIT_OK
    captured = capsys.readouterr()
    assert "Developer Environment Diagnostics Report" in captured.out
    assert "Overall status: OK" in captured.out
    assert "Exit code: 0" in captured.out


def test_cli_output_file_written(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "min_python_version": [3, 0],
                "min_free_disk_gb": 0.001,
                "required_env_vars": [],
                "required_tools": {},
                "disk_path": str(tmp_path),
            }
        )
    )
    out_file = tmp_path / "report.json"
    exit_code = main(
        ["--config", str(config_file), "--json", "--output", str(out_file), "--quiet"]
    )
    assert exit_code == EXIT_OK
    assert out_file.exists()
    payload = json.loads(out_file.read_text())
    assert payload["overall_status"] == "OK"


def test_cli_disk_path_override(tmp_path):
    exit_code = main(["--disk-path", str(tmp_path), "--quiet"])
    # Just verifying it runs to completion without raising.
    assert exit_code in (0, 1, 2)


def test_cli_version_flag(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "devenv-diag" in captured.out
