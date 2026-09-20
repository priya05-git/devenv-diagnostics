# devenv-diagnostics

A distributable command-line tool that inspects a machine and produces a
**deterministic developer-environment health report** — as structured JSON
or as a human-readable summary.

Built for the RabTech Python Software Engineering internship task
*"Packaged CLI Diagnostics Tool."*

## What it checks

| Check                    | What it verifies                                                         |
|---------------------------|---------------------------------------------------------------------------|
| `python_version`          | The running interpreter meets a configurable minimum version.            |
| `disk_space`               | Free disk space at a given path meets a configurable minimum (GB).       |
| `environment_variables`   | A configurable list of environment variables is set and non-empty.       |
| `developer_tools`         | A configurable list of CLI tools (git, docker, node, ...) is installed and, optionally, meets a minimum version. |

Every check is isolated: if one check raises an unexpected exception, it is
recorded as a single `ERROR` result rather than crashing the whole run.

## Installation

Requires Python 3.9+.

```bash
# From a clone of this repository, in an isolated virtual environment:
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"        # installs the package + pytest for running tests
```

This registers the `devenv-diag` console command via the `[project.scripts]`
entry point in `pyproject.toml` — no `python -m` prefix needed.

To build a distributable wheel/sdist instead:

```bash
pip install build
python -m build          # produces dist/*.whl and dist/*.tar.gz
pip install dist/*.whl    # install the built wheel anywhere
```

## Usage

```bash
devenv-diag                              # human-readable report to stdout
devenv-diag --json                       # structured JSON to stdout
devenv-diag --config myconfig.json       # use custom thresholds/requirements
devenv-diag --output report.json --json  # write report to a file
devenv-diag --disk-path /var             # check disk space at a specific path
devenv-diag --quiet --output report.json # write to file only, no stdout
devenv-diag --version
```

### Example: human-readable output

```
============================================================
  Developer Environment Diagnostics Report
============================================================
Generated at : 2026-09-14T15:25:34.865059+00:00
Hostname     : vm
Tool version : 1.0.0
Config file  : (defaults)
------------------------------------------------------------
[OK]    python_version: Python 3.12.3 meets the minimum required version 3.9.
[OK]    disk_space: 9.95 GB free on '.' (minimum 5.0 GB).
[OK]    environment_variables: All 2 required environment variable(s) are set.
[OK]    developer_tools: All 2 configured developer tool(s) are installed and meet version requirements.
------------------------------------------------------------
Summary: 4 checks -- 4 ok, 0 warn, 0 error
Overall status: OK
Exit code: 0
============================================================
```

See `samples/` for full worked examples, including a failing run and a
malformed-config run.

### Configuration file

By default the tool requires `PATH` and `HOME` to be set, `git` and
`python3` to be installed, Python `>= 3.9`, and `5 GB` free disk space on
`.`. Override any of these with a JSON file passed via `--config`:

```json
{
  "min_python_version": [3, 10],
  "min_free_disk_gb": 10,
  "required_env_vars": ["PATH", "HOME", "RABTECH_API_KEY"],
  "required_tools": {
    "git": null,
    "docker": null,
    "node": "18.0.0"
  },
  "disk_path": "."
}
```

- `required_tools` maps a tool name to either `null` (just check it's
  installed) or a minimum version string (checked with a best-effort
  `tool --version` parse).
- Fields you omit fall back to the defaults above.

An invalid `--config` (missing file, broken JSON, or a value of the wrong
type/shape) is rejected with a specific error message and exit code `3`
**before** any checks run — see `samples/sample_config_malformed.json` and
`samples/sample_output_malformed_config.txt`.

## Exit codes

| Code | Meaning                                                            |
|------|---------------------------------------------------------------------|
| `0`  | All checks passed.                                                 |
| `1`  | At least one check produced a warning; nothing failed outright.    |
| `2`  | At least one check failed (e.g. a required tool is missing).       |
| `3`  | The `--config` file was missing, malformed, or had an invalid shape.|
| `4`  | An unexpected internal error occurred while running diagnostics.   |

Exit codes make the tool easy to use in CI (`devenv-diag || exit 1`) or as
a pre-flight check in setup scripts.

## Output format (`--json`)

```jsonc
{
  "tool": "devenv-diagnostics",
  "tool_version": "1.0.0",
  "generated_at": "2026-09-14T15:25:34.865059+00:00",
  "hostname": "vm",
  "config_source": null,
  "overall_status": "OK",     // worst of OK / WARN / ERROR across all checks
  "exit_code": 0,
  "checks": [
    {
      "name": "python_version",
      "status": "OK",
      "message": "Python 3.12.3 meets the minimum required version 3.9.",
      "details": { "...": "..." }
    }
  ],
  "summary": { "total": 4, "ok": 4, "warn": 0, "error": 0 }
}
```

Each check's `details` object carries machine-readable specifics (paths,
versions, byte counts) so the JSON output can be consumed by other tooling
without re-parsing the human-readable message.

## Sample reports

The `samples/` directory contains pre-generated output for the three main
scenarios covered by the test suite:

| File                                       | Scenario                                            |
|--------------------------------------------|------------------------------------------------------|
| `sample_report_success.json` / `.txt`      | All checks pass (default config).                    |
| `sample_config_strict.json`                | An intentionally strict config...                    |
| `sample_report_failing.json` / `.txt`      | ...producing missing-dependency / threshold failures. |
| `sample_config_malformed.json`             | A config file with invalid JSON...                    |
| `sample_output_malformed_config.txt`       | ...and the resulting exit-code-3 error.                |

## Running the tests

```bash
pip install -e ".[dev]"
pytest                          # run the suite
pytest --cov=devenv_diagnostics --cov-report=term-missing   # with coverage
```

The suite (`tests/`) covers:

- **Success paths** — every check passing, JSON and text rendering, exit
  code `0` (`test_cli.py::test_cli_success_path_exits_zero`, etc.).
- **Missing dependency paths** — a required tool that isn't on `PATH`
  produces an `ERROR` result and exit code `2`
  (`test_checks.py::test_developer_tools_error_when_tool_missing`,
  `test_cli.py::test_cli_missing_dependency_path_exits_two`).
- **Malformed configuration paths** — a config file that isn't valid JSON,
  isn't a JSON object, has a missing file, or has fields of the wrong
  type/shape, each rejected with a specific `ConfigError` message and exit
  code `3` (`tests/test_config.py`,
  `test_cli.py::test_cli_malformed_config_path_exits_three`).

38 tests, ~92% statement coverage as of this writing.

## Project layout

```
devenv-diagnostics/
├── pyproject.toml
├── README.md
├── src/
│   └── devenv_diagnostics/
│       ├── __init__.py
│       ├── cli.py        # argparse entry point, wires everything together
│       ├── checks.py     # the four diagnostic checks
│       ├── config.py     # config loading + validation (ConfigError)
│       ├── models.py     # Status, CheckResult, Report, exit codes
│       └── report.py     # JSON / text rendering
├── tests/
│   ├── test_checks.py
│   ├── test_cli.py
│   ├── test_config.py
│   └── test_models.py
└── samples/
    ├── sample_config_strict.json
    ├── sample_config_malformed.json
    ├── sample_report_success.json
    ├── sample_report_success.txt
    ├── sample_report_failing.json
    ├── sample_report_failing.txt
    └── sample_output_malformed_config.txt
```

## Determinism note

Two fields vary run-to-run by design: `generated_at` (a UTC timestamp) and
`hostname`. Every other field — check names, statuses, messages, and the
overall summary — is fully determined by the machine's actual state and the
active configuration, so the same environment always produces the same
verdict.
