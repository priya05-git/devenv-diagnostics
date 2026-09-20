"""Tests for devenv_diagnostics.config -- success and malformed-config paths."""
import json

import pytest

from devenv_diagnostics.config import Config, ConfigError, load_config


def test_load_config_defaults_when_no_path():
    config = load_config(None)
    assert config == Config.default()
    assert config.source is None


def test_load_config_valid_file(tmp_path):
    config_file = tmp_path / "config.json"
    config_file.write_text(
        json.dumps(
            {
                "min_python_version": [3, 10],
                "min_free_disk_gb": 2,
                "required_env_vars": ["PATH"],
                "required_tools": {"git": "2.0.0"},
                "disk_path": ".",
            }
        )
    )
    config = load_config(str(config_file))
    assert config.min_python_version == (3, 10)
    assert config.min_free_disk_gb == 2.0
    assert config.required_env_vars == ["PATH"]
    assert config.required_tools == {"git": "2.0.0"}
    assert config.source == str(config_file)


def test_load_config_missing_file(tmp_path):
    missing = tmp_path / "does-not-exist.json"
    with pytest.raises(ConfigError, match="not found"):
        load_config(str(missing))


def test_load_config_malformed_json(tmp_path):
    """A file that isn't valid JSON at all -- the classic 'malformed config'."""
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{ this is not: valid json ,,, ")
    with pytest.raises(ConfigError, match="not valid JSON"):
        load_config(str(bad_file))


def test_load_config_top_level_not_object(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps([1, 2, 3]))
    with pytest.raises(ConfigError, match="top level"):
        load_config(str(bad_file))


def test_load_config_wrong_type_for_min_python_version(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps({"min_python_version": "3.9"}))
    with pytest.raises(ConfigError, match="min_python_version"):
        load_config(str(bad_file))


def test_load_config_negative_disk_space(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps({"min_free_disk_gb": -5}))
    with pytest.raises(ConfigError, match="min_free_disk_gb"):
        load_config(str(bad_file))


def test_load_config_required_env_vars_wrong_type(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps({"required_env_vars": "PATH"}))
    with pytest.raises(ConfigError, match="required_env_vars"):
        load_config(str(bad_file))


def test_load_config_required_tools_wrong_type(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps({"required_tools": ["git", "node"]}))
    with pytest.raises(ConfigError, match="required_tools"):
        load_config(str(bad_file))


def test_load_config_required_tools_bad_version_type(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(json.dumps({"required_tools": {"git": 2}}))
    with pytest.raises(ConfigError, match="required_tools"):
        load_config(str(bad_file))


def test_load_config_path_is_a_directory(tmp_path):
    with pytest.raises(ConfigError, match="not a file"):
        load_config(str(tmp_path))
