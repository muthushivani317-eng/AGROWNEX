# Disease detection backend TDD evidence

Source: implementation request derived from the disease-detection failure
analysis; no plan file was supplied.

## User journeys

- An authenticated farmer can see truthful availability without gaining model access.
- A controlled tester sees only technically ready, release-eligible workflows.
- Mobile receives one stable `{crops, crop_identification}` capability object.
- Operators cannot deploy a pilot image with missing dependencies or model bundles.
- Clients receive precise standard error envelopes for operational model failures.

## Evidence

| Guarantee | Test target | Type | Result | Evidence |
|---|---|---|---|---|
| Capabilities combine registry, executable readiness, role, and release policy | `tests/test_disease_capability_contract.py` | Unit/integration | PASS | RED: missing service, then shape mismatch; GREEN: 4 passed |
| Conflicting controlled roles remain fail-closed | `test_conflicting_controlled_roles_match_fail_closed_auth_boundary` | Unit | PASS | RED: capabilities advertised authorization; GREEN after exact-one-role rule |
| FastAPI `HTTPException` uses the documented envelope | `tests/test_http_exception_contract.py` | API | PASS | RED: default `detail` response; GREEN with standard handler |
| Runtime failures map to stable non-sensitive codes | `tests/test_disease_runtime_error_mapping.py` | Unit | PASS | RED: missing mapper; GREEN with three public categories |
| Required Python packages and model workflow parts are inventoried | `tests/test_model_inventory.py` | Unit | PASS | RED: missing inventory module; GREEN after fail-closed inventory |
| Registry policy is shared by advertised and enforced crop authorization | `tests/test_crop_authorization_policy.py` | Unit | PASS | RED: missing shared policy; GREEN with exact-one-role and pilot eligibility checks |
| Technical readiness remains cached until explicit refresh | `tests/test_readiness_cache.py` | Unit | PASS | RED: missing cache module; GREEN with deterministic refresh behavior |
| Typed capabilities appear in OpenAPI | `test_capability_response_is_a_typed_openapi_contract` | API schema | PASS | RED: endpoint had no response model; GREEN with typed success envelope |
| HTTP exception headers survive normalization | `tests/test_http_exception_contract.py` | API | PASS | `Retry-After` retained in the standard envelope response |
| Existing controlled inference and readiness behavior remains compatible | focused command below | Integration | PASS | `121 passed in 23.48s` |
| Frozen inventory loads in the declared project environment | `python -m scripts.verify_model_inventory` | Deployment smoke | PASS | All dependencies, six disease runtimes, crop ID, and safety gate reported true |
| Changed Python files meet lint policy | focused Ruff command | Static | PASS | `All checks passed!` |

Focused integration command:

```text
PYTHONPATH=<repository-root>;<backend> .venv/Scripts/python -m pytest
tests/test_crop_authorization_policy.py tests/test_readiness_cache.py
tests/test_disease_runtime_error_mapping.py
tests/test_http_exception_contract.py tests/test_disease_capability_contract.py
tests/test_crop_capabilities.py tests/test_model_inventory.py tests/test_probes.py
tests/test_railway_runtime_readiness.py tests/test_restricted_crop_e2e.py
tests/test_legacy_joint_integration.py tests/test_crop_identity_access_control.py
tests/test_model_inventory.py app/banana_v3/tests -q
```

## Coverage and known gaps

The configured virtual environment does not contain the optional `pytest-cov`
plugin, so a local coverage percentage was not produced. CI installs
`pytest-cov` and retains the repository-wide 85% coverage gate. No tests were
skipped in the focused 100-test validation. Container construction itself was
not run locally; both Dockerfiles and CI execute the same passing inventory
command during delivery.

No TDD checkpoint commits were created because the user explicitly requested
that changes not be committed. RED and GREEN command evidence is recorded here.
