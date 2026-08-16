# Unresolved blockers

1. Railway `/api/v1/auth/otp/verify` returns HTTP 500 after Firebase OTP verification succeeds.
2. The sanitized server traceback/request correlation and Railway migration state have not been inspected.
3. Firebase Admin production configuration must be verified without exposing credentials.
4. Tamil authentication copy requires human product-language approval.

Farmer release readiness remains **NO** until the backend session exchange succeeds and the complete flow is retested on the physical device.
