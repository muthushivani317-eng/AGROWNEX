# AgrowAI — Mobile App Excellence Prompt (for Claude Code)

Run from repo root after the backend hardening phases. Target:
`agrow-ai/` (Expo SDK 57, expo-router, i18next ta/en, zustand,
react-query, MMKV).

---

You are the senior mobile engineer on AgrowAI. Our users are small
farmers in South Tamil Nadu: many are first-time smartphone users, many
read Tamil slowly or not at all, most use budget Android phones
(2–4GB RAM) on patchy 2G/3G networks, often outdoors in bright
sunlight. Every decision below optimizes for THAT user, not for us.
Work through the phases in order; after each phase run
`npx tsc --noEmit` and `npx jest`, fix breakage, add tests for new
logic, and commit.

## PHASE A — First-open experience (the KVK demo moment)
- Time-to-first-diagnosis is our north-star flow. From a cold open, a
  logged-in farmer must reach the disease camera in ONE tap from home.
  Redesign the home screen so the top card is a large "படத்தை எடு /
  Take Photo" action (min touch target 64dp), followed by today's
  weather and today's top mandi price for the farmer's primary crop.
  No feature grid of 20 icons — show the 4 live features only.
- Guest/demo mode: allow browsing weather + market + a sample disease
  result WITHOUT login, with login required only when saving or
  scanning. KVK sessions die when 50 farmers hit OTP at once; demo
  mode keeps the room moving.
- Onboarding: max 3 screens, illustration-led, ≤10 words per screen,
  Tamil default, with a skip. Ask only district + primary crop
  (everything else collected progressively later).
- Add haptic + audible confirmation (short Tamil voice cue via TTS
  seam) when a photo is captured and when a diagnosis arrives.

## PHASE B — Low-literacy & accessibility (our real moat)
- Voice-first surfaces: every primary screen gets a mic button that
  routes to the /ai/voice endpoint. The chat screen defaults to voice
  input with text as secondary.
- Add a "read aloud" (speaker icon) on every AI response, diagnosis
  result, weather alert, and price card — TTS via the backend seam,
  cached audio in MMKV keyed by content hash.
- Iconography audit: every navigation destination has a distinct,
  literal icon (leaf+magnifier for disease, cloud for weather, scales
  for market). Never rely on text alone for navigation.
- Typography: Noto Sans Tamil at a minimum 18sp body size, high
  contrast theme meeting WCAG AA in bright sunlight (test both
  themes), no thin font weights.
- Accessibility pass: accessibilityLabel (in the active locale) on all
  touchables, screen-reader order verified on the 3 core flows,
  dynamic font-scale support without layout breakage.

## PHASE C — Offline-first & flaky networks
- Wrap react-query with a persisted cache (MMKV persister). Weather,
  market prices, past diagnoses, and the crop calendar must render
  instantly from cache with a "last updated" timestamp, then refresh.
- Disease scan queue: if upload fails, store photo + metadata in an
  MMKV-backed queue, show it as "waiting for network" in history, and
  auto-flush with exponential backoff on reconnect (NetInfo listener).
  Never lose a farmer's photo.
- Image handling: compress captured photos client-side to ≤1MB /
  1600px longest edge before upload (expo-image-manipulator);
  disease-detection accuracy is unaffected but a 2G upload becomes
  feasible.
- Add a global offline banner (Tamil/English) and per-screen empty
  states that distinguish "offline" from "no data yet" — never a
  blank screen, never an English-only error.

## PHASE D — Performance on budget Android
- Cold start budget: ≤2.5s to interactive on a mid-range device.
  Audit and defer: load fonts with splash-screen hold, lazy-load
  admin/expert/satellite routes, remove any unused deps from the
  bundle, enable Hermes (verify it's on) and R8 shrinking in the
  production build.
- List performance: all history lists (diagnoses, chats, prices,
  notifications) use FlashList or FlatList with getItemLayout,
  memoized rows, and pagination from the API — no full-table fetches.
- expo-image everywhere with disk caching for diagnosis photos and
  recycled keys in lists.
- Add a simple performance test doc: measured cold start, screen
  transition times, and APK size before/after, recorded in
  PERF_REPORT.md.

## PHASE E — Retention loops (CRO priorities, in-app)
- Push notification deep links: weather alert → weather detail,
  price spike on farmer's crop → market screen, "your scan was
  reviewed by expert" → diagnosis detail. Wire notification taps
  through expo-router deep links; test all three.
- Personalized daily card: one home-screen card that rotates —
  today's actionable tip generated from the farm-memory context
  (crop stage + weather), in simple Tamil. Backed by a cached
  backend endpoint, one Flash call per farmer per day max.
- Diagnosis follow-up: 3 days after a disease diagnosis, schedule a
  local notification asking "did the treatment help?" with a
  one-tap better/same/worse response posted to the backend — this
  becomes our outcome dataset and the farmer feels cared for.
- Referral: a "share AgrowAI" action that shares a localized message
  + store link via the system share sheet (farmers share on
  WhatsApp themselves — we get WhatsApp distribution without
  building WhatsApp).

## PHASE F — Store readiness & polish
- App identity: proper adaptive icon, splash, and store metadata
  drafts (title, short/long description) in Tamil and English in
  `store/` folder. Screenshots checklist documented.
- Android: verify targetSdk meets current Play policy, add
  Data Safety form answers as a doc (what we collect, why, deletion
  path), request only camera/location/notification permissions with
  in-context rationale strings in Tamil BEFORE the system prompt.
- Crash-free target: integrate sentry-expo (reuse backend DSN
  project family), add an error boundary per route group with a
  friendly Tamil recovery screen and a "report" action.
- In-app account deletion (Play policy requirement) wired to the
  backend deletion endpoint, with clear Tamil confirmation.
- EAS build profiles (development/preview/production) documented in
  BUILD.md, with env-driven API base URL per profile.
- Final sweep: remove all remaining mock frontend providers from
  production builds via env flag, ensure every user-visible string
  goes through i18next (grep for hardcoded literals), and run the
  full jest suite + tsc clean.

Ship quality bar: a 60-year-old farmer who has never installed an
app should be able to photograph a sick leaf and hear the diagnosis
read aloud in Tamil within 90 seconds of first open, on a slow
network, without help. Every phase serves that sentence.