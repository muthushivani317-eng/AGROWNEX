# Root cause

The original mobile failures had three grounded causes: critical native input visibility depended on styling that was not reliable in the release bundle; the OTP control placed its authoritative input over the visual cells; and unknown confirmation/backend errors were mapped to generic or misleading messages.

Those mobile defects are fixed and physically validated. The remaining authentication failure occurs after Firebase accepts the OTP. The request to `/api/v1/auth/otp/verify` reaches the backend and returns HTTP 500 (`internal_error`), preventing the app session from being established.

The exact server exception is not available locally. Possible causes such as an unapplied Railway database migration or invalid Firebase Admin runtime configuration must remain hypotheses until sanitized Railway logs and deployment state are inspected.
