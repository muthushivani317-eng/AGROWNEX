# Firebase OTP KVK field-test TDD evidence

## Scope

The acceptance criteria came from the attached REAL FIREBASE OTP diagnosis and
completion request. No checkpoint commits were created because that request
explicitly prohibits commits and pushes.

## User journeys

- A KVK field tester sees real phone authentication, never a development/test
  login implication.
- If Firebase configuration is unavailable, authentication fails closed with a
  translated unavailable message and never selects the mock provider.
- Explicit development tests may still inject the mock provider.

## RED / GREEN evidence

| Guarantee                                                                      | Test                                                            | RED                                                                 | GREEN        |
| ------------------------------------------------------------------------------ | --------------------------------------------------------------- | ------------------------------------------------------------------- | ------------ |
| KVK missing-Firebase behavior selects no mock and reports Firebase unavailable | `features/auth/__tests__/firebasePhoneProductionSafety.test.ts` | 2 intended failures: `authAvailabilityMessageKey is not a function` | 19/19 passed |
| Development-only mock wording is not used by configured KVK builds             | same                                                            | intended missing policy helper                                      | passed       |

RED and GREEN command:

`npm test -- --runInBand features/auth/__tests__/firebasePhoneProductionSafety.test.ts`

## Focused regression evidence

- Mobile auth, OTP input, startup, and profile tests: 17 suites, 119 tests passed.
- Backend auth, Firebase-token boundary, profile, access-control, and farm-team
  tests: 54 tests passed.

Automated Firebase mocks prove wiring and error handling only. They do not prove
real SMS delivery, Firebase Console signing registration, or physical-device
behavior.
