# Feature 6A Soil Scan TDD evidence

## RED

`python -m pytest tests/test_soil_scan_engine.py -q` failed during collection with
`ModuleNotFoundError: app.modules.soil.scan` before the implementation existed.

The persistence and terrain tests also failed before implementation because scan
record repository methods and the fail-closed terrain provider contract did not
exist.

## GREEN

The focused engine suite covers every named output, invalid AOI behavior, the
absence of fabricated pH/EC/sample coordinates, deterministic variability-derived
sampling, point-in-AOI enforcement, and rejection of sample/outside-AOI zones.
The service test proves a non-sample spatial satellite product with scene
provenance creates and persists an inside-AOI sampling plan. Repository/API tests
cover latest, history, detail, ownership, and immutable snapshots. Broader Soil,
Weather, Satellite, Waterlogging, and Farm tests verify the shared contracts.

Mobile tests cover response mapping, persisted sampling-plan mapping, and
user/farm-scoped cache isolation. TypeScript compilation verifies the map and
screen integration. The map renders only persisted points supplied by the backend.

The current Copernicus adapter does not yet produce the spatial-zone product and
credentials are absent in the validation environment. Production therefore
returns an explicit insufficient-spatial-evidence state and no sampling points.
This is a tested fail-closed path, not a real-world provider validation claim.

## Final validation

- Focused backend shared regressions: 157 passed.
- Focused mobile shared regressions: 21 suites / 104 tests passed.
- Soil final backend check: 35 passed; changed-scope Ruff passed.
- Mobile TypeScript and changed-scope Prettier checks passed.
- Full backend: 1049 passed, 7 failed, 1 skipped; the failures require the
  unrelated missing ONNX runtime dependency.
- Full mobile: 171 suites passed, 2 failed; both failures are unrelated brittle
  source-text assertions in Disease and Notification tests.
- Physical Android validation was not run because `adb devices` found no device.
