# Firebase and backend boundary analysis

Physical-device evidence proves that the Firebase phone-auth request returned a confirmation flow and that Firebase accepted the entered OTP. The app then attempted the backend session exchange through `/api/v1/auth/otp/verify`.

The backend exchange returned HTTP 500 with the sanitized API category `internal_error`. The client correctly maps this to `auth.serviceUnavailable`; it does not expose a raw localization key, Firebase credential, token, phone number, OTP, or internal server detail.

The Firebase Android package/project configuration is present locally, but console-side registration of the release signer must be verified against the official Firebase Console. The backend HTTP 500—not SMS dispatch or Firebase OTP confirmation—is the active blocker.
