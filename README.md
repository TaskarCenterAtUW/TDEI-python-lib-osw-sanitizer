# OSW Sanitizer

[![Unit Tests](https://github.com/TaskarCenterAtUW/TDEI-python-lib-osw-sanitizer/actions/workflows/unit_tests.yml/badge.svg)](https://github.com/TaskarCenterAtUW/TDEI-python-lib-osw-sanitizer/actions/workflows/unit_tests.yml)
[![Coverage](https://img.shields.io/badge/coverage-%3E90%25-brightgreen)](#testing)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![Package](https://img.shields.io/badge/package-osw--sanitizer-blue)](https://github.com/TaskarCenterAtUW/TDEI-python-lib-osw-sanitizer)

`osw-sanitizer` is a Python package for sanitizing OpenSidewalks (OSW)
dataset ZIP files. It is designed to be consumed by the TDEI sanitization
service and by other Python workflows that need the same deterministic cleanup
behavior.

## Features

- Removes JSON `null` and numeric `NaN` property values.
- Preserves string values such as `"None"`, `"null"`, `"nan"`, `"n/a"`, and `"na"`.
- Truncates geometry coordinates to a configurable precision.
- Removes unsupported non-OSW files from sanitized output.
- Removes zero-length edge `LineString` features unless explicitly allowed.
- Splits edge `LineString` features that exceed the configured geometry vertex limit.
- Generates intermediate split nodes and rewires `_u_id` / `_v_id` references when needed.
- Writes a `fixes.json` artifact describing every applied change.

Polygon splitting is intentionally out of scope.

## Installation

```bash
pip install osw-sanitizer
```

For local development:

```bash
python -m pip install -e .
python -m pip install pytest coverage
```

## Quick Start

```python
from osw_sanitizer import OSWSanitization, SanitizationConfig

config = SanitizationConfig(
    coordinate_precision=7,
    max_geometry_vertices=2000,
    allow_zero_length_lines=False,
)

sanitizer = OSWSanitization(
    input_path="/path/to/input.zip",
    output_dir="/path/to/output",
    config=config,
)

result = sanitizer.sanitize()

if result.success:
    print(result.updated_dataset_zip)
    print(result.fixes_json)
else:
    print(result.message)
```

## Service-Compatible API

`OSWSanitization.sanitize_dataset(...)` returns a dictionary with the same keys
used by `TDEI-sanitization-service`:

```python
from osw_sanitizer import OSWSanitization

result = OSWSanitization.sanitize_dataset(
    input_zip_path="/path/to/input.zip",
    output_dir="/path/to/output",
)

print(result["success"])
print(result["updated_dataset_zip"])
print(result["fixes_json"])
```

## Configuration

| Option | Default | Description |
|---|---:|---|
| `coordinate_precision` | `7` | Maximum decimal places retained for coordinate values. |
| `max_geometry_vertices` | `2000` | Splits edge `LineString` features with more vertices than this value. |
| `allow_zero_length_lines` | `False` | Preserves zero-length edge `LineString` features when `True`; otherwise they are removed. |

The configuration names match the OSW formatter and validator packages where
applicable.

## Output Artifacts

The sanitizer writes two artifacts into `output_dir`:

- A sanitized dataset ZIP using the same filename as the input ZIP.
- `fixes.json`, containing structured details about applied fixes.

The result object exposes both paths:

```python
result.updated_dataset_zip
result.fixes_json
```

## fixes.json

`fixes.json` includes:

- `removedTags`
- `precisionUpdates`
- `removedEdges`
- `splitEdges`
- `addedNodes`
- `removedFiles`

Example:

```json
{
  "jobId": "",
  "files": [
    {
      "filename": "edges.geojson",
      "removedTags": [
        {
          "featureIndex": 0,
          "tag": "width",
          "value": null
        }
      ],
      "precisionUpdates": [
        {
          "featureIndex": 0,
          "coordinatePath": "coordinates[0]",
          "original": "-122.123456789",
          "updated": "-122.1234567",
          "precision": 7
        }
      ]
    }
  ],
  "removedFiles": []
}
```

## Supported Dataset Files

The sanitizer keeps OSW dataset files matching these dataset keys:

- `edges`
- `lines`
- `nodes`
- `points`
- `polygons`
- `zones`

Supported filename forms include:

- `<dataset>.geojson`
- `<dataset>.OSW.geojson`
- `*.<dataset>.geojson`
- `*.<dataset>.OSW.geojson`

Unsupported files are omitted from sanitized output and recorded in
`fixes.json`.

## Testing

Install the package and test dependencies:

```bash
python -m pip install -e .
python -m pip install pytest coverage
```

Run the unit tests:

```bash
python -m pytest
```

Run the unit tests with coverage enforcement:

```bash
coverage run -m pytest
coverage report --fail-under=90
```

The GitHub Actions unit test workflow writes timestamped test and coverage
logs into `test_results/` and uploads them to Azure Blob Storage using the
`AZURE_STORAGE_CONNECTION_STRING` secret.

Package metadata is defined in `pyproject.toml`. `setup.py` is retained as a
compatibility shim for legacy packaging workflows.

## Release Pipelines

GitHub Actions includes package publishing workflows:

- `.github/workflows/deploy_to_test.yml` publishes to TestPyPI from `develop`.
- `.github/workflows/publish_to_pypi.yml` publishes to PyPI from semver tags or manual dispatch.

Both workflows build the package from `pyproject.toml` and use
`PYPI_API_TOKEN` for authentication.

## Test Datasets

Sample dataset ZIPs are checked in under `tests/assets` and are used by the
unit tests:

- `precision_and_null_tags.zip`
- `zero_length_edge.zip`
- `oversized_edge.zip`
- `unsupported_files.zip`
- `nested_dataset.zip`
