# Route map

| File | Path | Parent | Guard/result | Visible component |
|---|---|---|---|---|
| `app/index.tsx` | `/` | root | temporary resolving surface; central guard replaces it | `RouteResolvingScreen` |
| `app/(auth)/language.tsx` | `/(auth)/language` | auth stack | fresh unauthenticated state | `LanguageSelectScreen` |
| `app/(auth)/login.tsx` | `/(auth)/login` | auth stack | language selected, unauthenticated | `LoginScreen` |
| `app/(auth)/otp.tsx` | `/(auth)/otp` | auth stack | OTP request succeeded | `VerifyOtpScreen` |
| `app/(auth)/verify.tsx` | `/(auth)/verify` | auth stack | retained compatibility alias | `VerifyOtpScreen` |
| `app/(auth)/complete-profile.tsx` | `/(auth)/complete-profile` | auth stack | authenticated, profile incomplete | profile completion |
| `app/(tabs)/index.tsx` | `/(tabs)` | tab stack | authenticated, profile complete | `HomeScreen` |

`useStartupRouteGuard` is the sole startup route resolver. Language confirmation now routes directly to phone login as required. Login success routes to the explicitly registered OTP screen.
