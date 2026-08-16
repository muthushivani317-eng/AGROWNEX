# AgrowAI remaining phone-authentication failures

Status: **MOBILE_AND_FIREBASE_FLOW_PASS; BACKEND_SESSION_EXCHANGE_FAILED_HTTP_500**

Physical-device validation confirmed that the phone number is visible, the OTP screen renders one digit per box, Firebase returns an OTP confirmation flow, and the entered OTP is accepted by Firebase. The subsequent authenticated backend exchange at `/api/v1/auth/otp/verify` returns HTTP 500 with the safe category `internal_error`. The app now renders a localized service-unavailable message instead of a raw key or misleading invalid-OTP message.

- PHONE_NUMBER_VISIBLE=PASS
- PHONE_TEXT_CONTRAST=PASS
- OTP_DUPLICATE_RENDERING_FIXED=PASS
- OTP_ONE_DIGIT_PER_BOX=PASS
- RAW_LOCALIZATION_KEY_REMOVED=PASS
- ERROR_MESSAGES_LOCALIZED=PASS; TAMIL_DRAFT_REQUIRES_HUMAN_PRODUCT_REVIEW
- E164_NORMALIZATION=PASS
- FIREBASE_REQUEST_CONFIRMED=PASS
- OTP_NAVIGATION_GUARD=PASS
- SMS_REQUEST=PASS_BY_RECEIVED_OTP_AND_FIREBASE_CONFIRMATION
- FIREBASE_OTP_VERIFICATION=PASS
- BACKEND_SESSION_EXCHANGE=FAIL_HTTP_500
- RELEASE_BUILD=PASS
- DEVICE_UI_VALIDATION=PASS
- AUTH_FLOW=FAIL_BACKEND_SESSION_ESTABLISHMENT
- FARMER_RELEASE_READINESS=NO

APK: `D:\AgrowAI\AgrowAi_app\agrow-ai\android\app\build\outputs\apk\release\app-release.apk`

APK SHA-256: `12c7f0ef29000f8f039525f6a28cac9dc07c2b615782eca50e952ea2e2208263`

The remaining fix requires sanitized Railway server diagnostics and migration/runtime-state verification. A database migration problem is a hypothesis, not a confirmed root cause.
