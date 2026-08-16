# APK string provenance

APK: `D:\AgrowAI\AgrowAi_app\agrow-ai\android\app\build\outputs\apk\internalTesting\app-internalTesting.apk`

Hermes bundle bytes: 7620428

## Conclusion

- Active application-owned loopback endpoint: **No**
- Unreachable dependency loopback strings: **Yes**
- Runtime fixed-OTP bypass: **No**
- Unreachable test/example OTP strings: **Yes**
- Production API base URL is injected at build time and validated as public HTTPS; missing/unsafe values fail build and startup.

## Exact string groups

- `http://localhost`: offsets 869193
- `localhost`: offsets 869200, 1064469, 1656948
- `127.0.0.1`: offsets 875135, 1291249
- `10.0.2.2`: offsets 952495, 1064484, 1291264
- `development_mock`: offsets 1032735
- `mockAuthProvider`: offsets 1681498

Six-digit candidate values inventoried: 24. Every occurrence and offset is recorded in the JSON. Only `000000` and `123456` were OTP-relevant review values; neither is consumed by the internal-testing auth path.

## Provenance

### UNREACHABLE_DEPENDENCY_TEXT

Values: `http://localhost`, `localhost`

Origins: react-native/Libraries/Core/Devtools/getDevServer.js; @expo/metro-runtime error/source URL support; axios/lib/platform/common/utils.js; @react-native-firebase/auth/lib/namespaced.ts emulator helper

Import chain: Expo/React Native bootstrap and apiClient -> axios; authProvider -> @react-native-firebase/auth

Reachability: Text/module present; not an AgrowAI API-base candidate. Axios origin fallback is not the Axios request baseURL.

Remediation: Retain dependency text; enforce application configuration and APK behavior with security-build-gates.js.

### UNREACHABLE_DEPENDENCY_TEXT

Values: `127.0.0.1`, `10.0.2.2`

Origins: @react-native-firebase/auth/lib/namespaced.ts useEmulator Android remapping; axios/lib/helpers/shouldBypassProxy.js loopback detection

Import chain: authProvider -> @react-native-firebase/auth; apiClient -> axios

Reachability: Dependency helper present but no application call/configuration can select it as an endpoint.

Remediation: No binary modification; preserve upstream package and fail builds on application-owned loopback URLs.

### UNREACHABLE_DEPENDENCY_TEXT

Values: `0.0.0.0`, `::1`

Origins: axios/lib/helpers/shouldBypassProxy.js loopback classification and framework networking utilities

Import chain: apiClient -> axios

Reachability: May classify a URL but cannot assign or override AgrowAI baseURL.

Remediation: Retain and document.

### NO_RUNTIME_OTP_BYPASS

Values: `development_mock`, `123456`, `000000`

Origins: agrow-ai/features/auth/services/authProvider.ts diagnostic category; @react-native-firebase/auth API examples; dependency numeric data; Jest tests excluded from runtime graph

Import chain: app auth store -> authProvider; authProvider selects Firebase for configured internal_testing

Reachability: Diagnostic/example text present; fixed values cannot create a credential or session.

Remediation: Negative tests cover 000000 and 123456; retain dependency examples and fail builds if a development OTP environment is configured.
