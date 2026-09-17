# Disease capability mobile TDD evidence

## Source and journeys

Journeys were derived from the disease-detection remediation request:

- An unauthorized farmer cannot upload a photo to a controlled crop-identification or disease runtime.
- An authorized tester sees only crops enabled by the server for their build and account.
- A server authorization or model failure is shown as its real category, not as an image-read failure.
- Runtime availability cannot be enabled by static mobile metadata.

## RED/GREEN evidence

| Guarantee | Test | RED evidence | GREEN evidence |
|---|---|---|---|
| Build profile and user authorization are both required | `features/multiCropDiagnosis/__tests__/cropRegistry.test.ts` | Missing resolver functions and transitional scopes failed | Capability policy tests pass |
| Only an authorized, allowlisted adapter can submit | `features/multiCropDiagnosis/__tests__/adapters.test.ts` | Authorized capability made zero requests before implementation | Adapter tests pass |
| Backend failures retain actionable categories | `features/multiCropDiagnosis/__tests__/responseParser.test.ts` | New cases returned `server_error` | Error mapping tests pass |
| Unauthorized users cannot start crop identification | `features/disease/__tests__/DiseaseScreen.test.tsx` | Capture UI remained available | Screen test passes and no model call occurs |
| Static metadata never grants inference access | `config/__tests__/cropCapabilities.test.ts` | Stale tests contradicted fail-closed metadata | Static metadata tests pass |

## Validation

- Focused integration command: 8 suites, 128 tests passed.
- `npm run typecheck`: passed.
- Focused coverage command: 66 tests passed. Function coverage was 81.08%; statement coverage was 68.13%. The lower statement result is mainly unexercised legacy confirmation/feedback branches; the new capability resolver itself reached 86.3% line coverage and 80.92% branch coverage.

## Known boundary

The mobile client calls authenticated `GET /disease/capabilities` through the shared `api.get` helper, so the standard success envelope is unwrapped. Missing or unknown security fields fail closed. The parser accepts documented transitional field aliases but never accepts a server-provided URL as an executable route.
