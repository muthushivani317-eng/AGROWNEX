# Firebase Phone Authentication production checklist

The Android app uses `@react-native-firebase/auth` native phone authentication.
Firebase sends and verifies the SMS; AgrowAI sends the resulting Firebase ID
token to the existing backend session endpoint. The backend must use
`OTP_PROVIDER=firebase` and must never send a second OTP.

Before a real-device pilot, an authorized Firebase administrator must:

1. Enable **Authentication > Sign-in method > Phone**.
2. Allow India in **Authentication > Settings > SMS region policy**.
3. Confirm Android package `com.agrowai.app` in project `agrow-ai-8ba58`.
4. Register SHA-256 for Play Integrity and SHA-1 for reCAPTCHA fallback.
5. Link the required Cloud Billing account and confirm the current SMS plan/quota.
6. Download a fresh `google-services.json` if Firebase indicates configuration changed.
7. Confirm the real pilot number is not configured as a fictional test number.

Release signing fingerprints currently produced by the checked-in Android
release keystore (verify again whenever signing credentials change):

- SHA-1: `C8:60:C8:A4:38:A9:E9:33:FF:F1:B6:81:8A:86:E2:6B:6E:F8:02:F2`
- SHA-256: `60:9B:18:93:93:84:D8:53:73:42:F8:2D:00:D4:E2:2D:73:91:9F:48:11:00:B2:75:74:D1:C5:1A:81:C1:AE:35`

After registering fingerprints, download the updated Android
`google-services.json`, replace `android/app/google-services.json`, rebuild the
release APK, and reinstall it before testing a real phone number.

Local debug fingerprints:

```powershell
cd D:\AgrowAI\AgrowAi_app\agrow-ai\android
.\gradlew.bat signingReport
```

For EAS/production credentials, inspect the Android credential in the EAS
dashboard or run `npx eas-cli credentials -p android`, download the authorized
keystore through the supported credential workflow, then use `keytool -list -v`
locally. Never paste the keystore password or private key into logs or source.

Expo Go cannot load React Native Firebase native modules. Use the checked-in
native Android project or an Expo development/production build.
