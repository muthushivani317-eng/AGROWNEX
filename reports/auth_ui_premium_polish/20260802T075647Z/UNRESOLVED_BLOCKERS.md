# Unresolved blockers

1. `BEFORE_OTP.png` and `AFTER_OTP.png` cannot be truthfully captured until the device operator supplies an owned test number and reaches the Firebase OTP screen.
2. OTP boxes, Verify, resend, change-number, and OTP error presentation pass source-contract/static tests but remain pending physical screenshot validation.
3. Keyboard usability is implemented with native Android `height` avoidance, but the connected handset did not accept automated ADB focus taps; manual interaction is required for final device acceptance.

No authentication bypass, fake OTP, or test phone identity was introduced to remove these blockers.
