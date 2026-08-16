# Internal-testing APK inspection

- APK: `D:\AgrowAI\AgrowAi_app\agrow-ai\android\app\build\outputs\apk\internalTesting\app-internalTesting.apk`
- SHA-256: `17c54c41c9988513e7175c217d1ecb3599791e68b962ab2e60f827203c17ac22`
- Application ID: `com.agrowai.app`
- Version code: `1`
- Version name: `1.0.0-INTERNAL-TEST`
- Debuggable: `false` (attribute absent from merged release-derived manifest)
- Cleartext traffic: `false`
- Release channel: `internal_testing`
- Production backend embedded: `https://agrowai-app-production.up.railway.app`
- Firebase project embedded: `agrow-ai-8ba58`
- Internal flags: enabled; all testable features enabled; developer mocks disabled; production auth/API enabled
- Expo Updates: disabled
- Developer launcher/menu components: not present in the manifest or APK file list

## Permissions

The merged manifest declares coarse/fine location, camera, Internet, record audio, vibration, wake lock, network state, biometric/fingerprint, legacy read/write external storage through SDK 32, Google services, dynamic receiver protection, install-referrer binding, and `SYSTEM_ALERT_WINDOW` contributed by the Expo/React Native dependency graph.

## Raw bundle provenance and reachability

The Hermes bundle contains the approved production backend and Firebase identifiers. It also retains generic dependency text for `localhost`, `127.0.0.1`, and `10.0.2.2`, plus non-authenticating numeric/example text. Source tracing attributes the loopback values to React Native/Expo development URL support, React Native Firebase's uncalled `useEmulator` helper, and Axios origin/proxy classification—not to AgrowAI endpoint configuration. The internal configuration cannot activate loopback endpoints or mock authentication: build validation requires public HTTPS and project `agrow-ai-8ba58`, `selectAuthProvider` uses production Firebase or fails closed, and the APK gate distinguishes unreachable dependency strings from application-owned endpoints. Exact offsets and conclusions are recorded in `APK_STRING_PROVENANCE.json` and `APK_STRING_PROVENANCE.md`.

No secret values are included in this report.
