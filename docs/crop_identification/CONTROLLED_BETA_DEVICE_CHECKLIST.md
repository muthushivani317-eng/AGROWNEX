# Controlled-beta real-device checklist

No item below is complete without request ID, HTTP status, safe backend-log evidence and a screenshot. Never substitute mocked CI results.

For every currently loadable crop, test a healthy image, disease image, wrong-crop image, non-plant image, blurred image, dark image, corrupt image, unsupported crop and low-confidence image. Record crop-ID status, farmer confirmation/correction, disease route/model version, qualitative confidence, abstention and recommendation suppression.

Verify cross-user, modified request ID, replay, expiry, image replacement, unsupported crop injection and direct disease-route access all fail closed. Verify no secret or raw image appears in logs.

Current audit state: `REAL_PROVIDER_VALIDATION=NOT_RUN`; `PHYSICAL_DEVICE_E2E=NOT_RUN`.
