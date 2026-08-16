# Manual actions required

1. Enable USB debugging, connect the phone, accept its authorization prompt, and
   verify `adb devices` reports `device`.
2. Resume installation using the APK recorded in `APK_METADATA.json`.
3. Provide an authorized Firebase test phone number only in the app UI.
4. Enter the received OTP manually when prompted.
5. After authenticated checks, disconnect ADB, stop laptop connectivity, and
   perform the supervised laptop-off reopen test.
