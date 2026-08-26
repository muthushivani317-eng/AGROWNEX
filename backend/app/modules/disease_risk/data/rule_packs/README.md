# Disease-risk rule packs

This directory is the **only** place that feeds `ACTIVE_RULE_REGISTRY`
(`app/modules/disease_risk/service.py`, loaded via
`app/modules/disease_risk/registry.py`'s `load_active_registry()`). It is
empty on purpose right now.

## Why it's empty

Disease Risk Alerts refuses to raise an alert for a crop/disease until a rule
pack here has real, source-cited epidemiological thresholds behind it. That's
a deliberate safety gate — the app would rather show "no verified guidance
available" than tell a farmer "conditions favour blast this week" based on a
guessed threshold. Nobody has populated this directory with real, cited
content yet, so every crop/disease combination is blocked.

**Do not add an entry here unless the conditions come from a genuine,
checkable agronomic/epidemiological source** (a KVK, ICAR, a state
agricultural university's plant pathology advisory, a published extension
bulletin, or equivalent). A made-up `source_references` entry or
`reviewer_id` is worse than no entry at all — it tells a farmer "this
guidance is real" when it isn't.

## Two ways a pack can go live — `approval_status`

- `"VERIFIED"` — an independent agronomist has personally reviewed this exact
  pack for AgrowAI and signed off. `reviewer_id` should be that person's real
  name/role.
- `"SOURCED_PUBLIC_REFERENCE"` — compiled from a real, cited public source
  (see above) but not personally reviewed by an independent agronomist for
  AgrowAI specifically. Still fully live and shown to farmers, still requires
  genuine `source_references`, but the app shows a distinct, honest label
  ("compiled from a public source, not independently reviewed") instead of
  claiming full expert verification. Product decision, 2026-08-17: show real,
  cited content rather than nothing, without ever blurring it with an actual
  expert sign-off.

Both statuses resolve for farmers. `"UNVERIFIED"` / `"PENDING_REVIEW"` are for
drafts you want tracked but not yet live.

## Adding a real rule pack

1. Get the actual epidemiological conditions from your agronomic source: for
   a specific crop + disease + region + season + confirmed growth stage, the
   weather conditions (temperature/humidity/rainfall/etc., with real
   thresholds and comparison operators) that indicate elevated risk.
2. Copy `_TEMPLATE.json.example` to `<crop_id>_<disease_id>.json` (e.g.
   `paddy_blast.json`) in this directory and fill in every field with the
   real data. Field-by-field meaning:
   - `pack_id` — a stable unique id for this pack (e.g. `"paddy-blast-tn"`).
   - `crop_id` / `disease_id` — lowercase, underscore ids. `crop_id` must
     match how crops are stored on the farm record (e.g. `"paddy"`).
   - `regions` — region codes this pack applies to (e.g. `["IN-TN"]`).
   - `seasons` — season values this pack applies to (`"kharif"`, `"rabi"`,
     `"summer"`).
   - `confirmed_stages` — the crop-growth-stage codes (matching
     `app/modules/calendar/data/verified_schedules/<crop>.json`'s
     `stages[].code` for the same crop, where one exists) this pack is valid
     for. A farmer whose confirmed stage isn't in this list gets
     `OUT_OF_SCOPE`, not a guess.
   - `required_weather_variables` — which of the app's weather fields
     (`temperature_c`, `humidity_pct`, `precipitation_mm`, `wind_speed_kmh`)
     the conditions below actually need.
   - `observation_window_hours` / `forecast_window_hours` — how far back/
     forward the underlying weather data should be considered representative
     (informational metadata for now; the engine currently evaluates a
     single weather snapshot — see `engine.py`).
   - `conditions` — the actual rule: each entry is
     `{"variable": "<weather field>", "operator": "gt|gte|lt|lte|eq", "value": <threshold>}`.
     ALL conditions must match for `RISK_CONDITIONS_PRESENT`; if some but not
     all match, the result is `CONDITIONS_NOT_MET`.
   - `minimum_data_completeness` — fraction (0-1) of
     `required_weather_variables` that must be present or the result is
     `INSUFFICIENT_DATA`.
   - `maximum_weather_age_hours` — how stale the weather snapshot can be
     before it's treated as unusable.
   - `cached_weather_allowed` — whether a cached (not live) weather reading is
     acceptable for this pack.
   - `alert_title_key` / `alert_explanation_key` — must point at real i18n
     keys added to `agrow-ai/localization/locales/en.ts` and `ta.ts` — the
     frontend looks these up for display.
   - `source_references` — the actual, real, checkable source document(s)
     (URL, bulletin title + publisher, etc.). Never a placeholder.
   - `reviewer_id` — see the two statuses above: a real agronomist's
     name/role for `VERIFIED`, or an honest description of who compiled/
     checked the sourced content (e.g. `"AgrowAI content team — compiled
     from cited public source, not independently agronomist-reviewed"`) for
     `SOURCED_PUBLIC_REFERENCE`. Never a fabricated name.
   - `approval_status` — `"VERIFIED"` or `"SOURCED_PUBLIC_REFERENCE"` to go
     live; `"UNVERIFIED"` / `"PENDING_REVIEW"` to track without activating.
   - `approved_at` — required (non-null) whenever `approval_status` is one of
     the two live statuses.
   - `review_expires_at` — must be in the future for the pack to be treated
     as live; an expired pack is silently excluded (not a crash). Plan to
     refresh before it expires.
   - `cooldown_hours` — minimum time between repeat alerts for the same
     farm/pack (prevents alert spam).
   - `alert_expiry_hours` — how long a generated alert stays valid.
   - `content_hash` — a SHA-256 over the pydantic-normalized pack (everything
     except `content_hash` itself), used to detect accidental edits after
     sign-off. **Don't hand-compute this.** Run:
     ```
     python scripts/compute_rule_pack_hash.py app/modules/disease_risk/data/rule_packs/<file>.json
     ```
     from the `backend/` directory — it validates the file against the
     schema and writes the correct `content_hash` in place.
3. Run the backend test suite (`pytest tests/test_disease_risk_engine.py
   tests/test_disease_risk_registry_loader.py`) after adding real packs.
4. Deploy. `ACTIVE_RULE_REGISTRY` loads every `*.json` file in this directory
   at import time — invalid or malformed files are skipped with a warning
   logged, not a startup crash, but that also means a typo silently leaves
   that crop/disease unfixed. Check deploy logs for `disease_risk.registry`
   warnings after every change here.

## What NOT to do

Don't invent epidemiological thresholds "because they sound plausible" — an
incorrect risk threshold could cause a farmer to either miss a real outbreak
window or spray/act unnecessarily. If you can't find a genuine, citable
source for a crop/disease combination, leave it out — the app's "no verified
guidance available" state is the honest answer, exactly like Crop Calendar's
equivalent gate.
