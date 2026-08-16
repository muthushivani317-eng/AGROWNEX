# R2 storage fail-closed TDD evidence

Source: the scoped R2 production-mock removal request supplied for this run.

## Guarantees

| Guarantee | Test | RED | GREEN |
|---|---|---|---|
| Missing R2 credentials never select `MockStorage` in production, internal testing, or KVK field testing | `tests/test_storage_provider_safety.py` | Missing unavailable provider import | 6 provider/consumer tests passed |
| Explicit test configuration can still select and inject `MockStorage` | `tests/test_storage_provider_safety.py` | Missing policy implementation | Passed |
| Controlled disease retention, Nutrient, and Growth receive fail-closed storage | `tests/test_storage_provider_safety.py` plus existing flow suites | Automatic mock URL was possible | 28 focused backend tests passed |
| Mobile Disease, Nutrient, and Growth present localized storage-unavailable states | nutrient/diagnosis parser and localization tests | Generic/server error mapping | 46 focused mobile tests passed |

## Validation

- Full backend: `1081 passed, 1 skipped`.
- Full mobile: `174 suites, 967 tests passed`.
- TypeScript typecheck, changed-file Ruff, changed-file Prettier, localization tests, backend startup, and 241-route check passed.

No commits were created because the source request explicitly prohibited commits.
