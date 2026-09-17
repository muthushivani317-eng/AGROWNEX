# 🌾 AgrowAI — Mobile App

Your AI Farming Partner. A Tamil-first, AI-powered Agriculture Operating System for
farmers in Tamil Nadu (expanding across India).

Built with **Expo (SDK 57) + Expo Router + TypeScript (strict)**, following the
**Feature-Based Clean Architecture** and design system defined in `docs/`. Those
documents (`AGROWAI_MASTER_SPEC.md`, `PRODUCT_RULES.md`, `DESIGN_SYSTEM.md`,
`FRONTEND_ARCHITECTURE.md`, `API_CONTRACT.md`, …) are the single source of truth.

> **Phase 1 (Foundation) — complete.** Architecture, navigation, theme, Tamil-first
> localization, reusable `Ag*` UI kit, state management, API client, MMKV/SQLite
> storage, and authentication scaffolding are in place. Business feature modules
> come in later phases. The FastAPI backend skeleton lives in `../backend`.

---

## Requirements

MMKV, SQLite, and (later) Mapbox/FCM are native modules, so the app runs on a
**custom Expo dev build**, not Expo Go.

```bash
npm install
cp .env.example .env        # optional — app runs without it (mock auth)

npx expo run:android        # or run:ios — builds the dev client
# then: npx expo start --dev-client
```

Quality gates:

```bash
npm run typecheck   # tsc --noEmit (strict)
npm test            # jest
```

### Auth in development

Firebase phone OTP requires configured `EXPO_PUBLIC_FIREBASE_*` env vars **and** a
dev build (reCAPTCHA/App Check). Without them the app transparently uses a **local
mock provider** — enter any valid 10-digit number and the dev OTP **`123456`**.

---

## Architecture (docs/FRONTEND_ARCHITECTURE.md)

```
app/                     Expo Router routes (thin — screens live in features/)
  _layout.tsx            Providers, fonts, i18n + DB + session bootstrap, splash, guard
  index.tsx              Cold-start redirect based on auth state
  (auth)/                onboarding · login · verify · complete-profile
  (tabs)/                home · ai · farm · market · profile

components/ui/           Ag* design-system kit (AgButton, AgInput, AgOtpInput,
                         AgDropdown, AgCard, AgText, AgChip, AgBadge, AgScreen,
                         AgSkeleton, AgEmptyState, AgErrorState, AgOfflineBanner…)
components/              Cross-feature widgets (AgLanguageToggle, AgThemeToggle,
                         AgComingSoon)
config/                  Typed env access + feature flags
constants/               Domain data (TN districts, common crops)
features/<feature>/      types · schemas · store · services · hooks · components · screens
  auth/                  Phone OTP + social login, session, profile, route guard
hooks/                   useAppTheme · useLanguage · useNetworkStatus
localization/            i18next setup + ta / en (Tamil is default)
lib/                     storage (MMKV + SecureStore key) · db (SQLite offline queue)
                         · queryClient · firebase · logger
providers/               AppProviders (Query · SafeArea · Gesture · BottomSheet) + ThemeController
services/                apiClient (axios, envelope, JWT, retry) · endpoints
stores/                  Global zustand stores (theme)
theme/                   Design tokens (mirror the CSS vars in global.css)
utils/                   cn · format · id
```

### Key decisions

- **Styling:** NativeWind v4. Tokens are CSS variables in `global.css` (exact
  DESIGN_SYSTEM palette, light + dark), mirrored in `theme/colors.ts` for
  imperative use. `useAppTheme()` returns the active palette; `ThemeController`
  syncs the persisted preference. **Lucide** icons throughout.
- **Typography:** Tamil-first — `AgText` auto-switches **Noto Sans Tamil** (Tamil)
  / **Inter** (English) per active language.
- **State/data:** Zustand (persisted in MMKV) + TanStack Query (server state only).
  Forms use React Hook Form + Zod.
- **Storage:** encrypted MMKV (AES-256, key in SecureStore) for tokens; app MMKV
  for prefs/cache; SQLite offline outbox for the sync queue.
- **API:** single `apiClient` (never fetch in screens) with JWT header,
  `X-Request-ID`, `Accept-Language`, retry/backoff, and the `API_CONTRACT` envelope.
- **Auth:** swappable `AuthProvider` (`mock` ↔ `firebase`) selected by
  `isFirebaseConfigured`, so screens never depend on the identity backend.
```
