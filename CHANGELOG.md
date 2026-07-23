# Changelog

## 0.1.1

- Bumped package version for PyPI republish after initial `0.1.0` release.
- Made `pyproject.toml` the single hardcoded version source.

## 0.1.0

- Added [#4091](https://dev.azure.com/TDEI-UW/TDEI/_workitems/edit/4091): initial `osw-sanitizer` Python package.
- Added public package API:
  - `OSWSanitization`
  - `SanitizationConfig`
  - `SanitizationResult`
  - `SanitizationProcessor` compatibility alias.
- Added configurable sanitizer behavior:
  - `coordinate_precision`, default `7`.
  - `max_geometry_vertices`, default `2000`.
  - `allow_zero_length_lines`, default `False`.
- Added OSW dataset sanitization support for:
  - Removing JSON `null` and numeric `NaN` property values.
  - Preserving string null-like values such as `"None"`, `"null"`, `"nan"`, `"n/a"`, and `"na"`.
  - Truncating coordinates to the configured precision.
  - Removing unsupported non-OSW files from sanitized output.
  - Removing zero-length edge `LineString` features when `allow_zero_length_lines=False`.
  - Preserving zero-length edge `LineString` features when `allow_zero_length_lines=True`.
  - Splitting edge `LineString` features exceeding `max_geometry_vertices`.
  - Generating intermediate split nodes when needed.
  - Rewiring `_u_id` and `_v_id` references for split edges.
- Added `fixes.json` reporting for:
  - Removed tags.
  - Coordinate precision updates.
  - Unsupported file removals.
  - Removed zero-length edges.
  - Split oversized edges.
  - Generated split nodes.
- Added package setup files:
  - `pyproject.toml`
  - `setup.py`
  - `requirements.txt`
  - `MANIFEST.in`
  - `version.py`
- Added package metadata, MIT license, typed package marker, and GitHub Actions unit test workflow.
- Expanded package documentation with API usage, configuration, supported files, output artifacts, and development instructions.
- Added unit tests for package API and sanitizer behavior.
- Added sample dataset ZIPs under `tests/assets`.
- Added coverage configuration with a 90% minimum threshold.
- Updated GitHub Actions to run tests with coverage enforcement.
- Updated GitHub Actions to upload timestamped test result logs to Azure Blob Storage.
- Added TestPyPI and production PyPI publishing workflows.
- Added README badges and explicit unit test / coverage commands.
