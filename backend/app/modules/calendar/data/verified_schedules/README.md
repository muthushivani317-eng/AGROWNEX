# Verified crop-stage schedules

This directory is the **only** place that feeds `ACTIVE_CROP_STAGE_REGISTRY`
(`app/modules/calendar/registry.py`). It is empty on purpose right now.

## Why it's empty

The Crop Calendar, Crop Growth Monitor, and Harvest Readiness features all
refuse to generate anything until a crop has a *verified* stage schedule here.
That's a deliberate safety gate (see `docs/` and `tests/test_calendar_registry.py`
and `tests/test_calendar_api_contract.py::...active_count == 0`) — the app
would rather show "not available" than hand a farmer AI-guessed or unreviewed
agronomic advice under the label "verified." Nobody has populated this
directory with real, expert-reviewed content yet, so every crop is blocked.

**Do not add an entry here unless the schedule comes from a genuine,
checkable public agricultural source** (a KVK, a state agricultural
university, ICAR, or equivalent) for the crop, region, and season it claims
to cover. An entry with a made-up `reviewer` or `source_organization` is
worse than no entry at all — it tells a farmer "this is verified" when it
isn't.

## Two ways a schedule can go live — `status`

- `"VERIFIED"` — an independent agronomist has personally reviewed this exact
  schedule for AgrowAI and signed off. `reviewer` should be that person's
  real name/role.
- `"SOURCED_PUBLIC_REFERENCE"` — compiled from a real, cited public source
  (see above) but not personally reviewed by an independent agronomist for
  AgrowAI specifically. Still fully live and shown to farmers, still requires
  genuine `source_organization`/`document_reference`, but the app shows a
  distinct, honest label ("compiled from a public source, not independently
  reviewed") instead of claiming full expert verification. Product decision,
  2026-08-17: show real, cited content rather than nothing, without ever
  blurring it with an actual expert sign-off.

Both statuses resolve for farmers. `"UNVERIFIED"` / `"EXPERT_REVIEW_PENDING"`
are for drafts you want tracked but not yet live.

## Adding a real schedule

1. Get the actual reviewed schedule from your agronomic source: for each
   growth stage, its day-offset window from sowing, and for each activity
   within a stage, what it is, when it happens (day offset from sowing), and
   whether it should trigger a farmer notification.
2. Copy `_TEMPLATE.json.example` to `<crop_id>.json` (e.g. `paddy.json`) in
   this directory and fill in every field with the real data. Field-by-field
   meaning:
   - `canonical_crop_id` — lowercase, underscore id (must match how crops are
     stored on the farm record, e.g. `"paddy"`, `"blackgram"`).
   - `aliases` — other names/spellings this schedule should also match
     (e.g. `["rice"]` for paddy). Matching is case-insensitive and
     space-to-underscore normalized (see `CropStageRegistry.resolve`).
   - `stages[].start_offset` / `end_offset` — the stage's day-offset window
     from sowing date (inclusive).
   - `stages[].activities[].day_offset` — the day, relative to sowing, this
     activity happens. Negative offsets are allowed (e.g. land prep before
     sowing).
   - `stages[].activities[].label_key` / `description_key` — must match the
     pattern `calendar.verified.<key>` / point at real keys added to
     `agrow-ai/localization/locales/en.ts` and `ta.ts` under
     `calendar.verified.*` — the frontend looks these up for display, it does
     not render the English text embedded in this JSON directly.
   - `stages[].label_key` — same idea, under `calendar.stages.*`.
   - `source_organization`, `document_reference`, `reviewer`, `approval_date`,
     `review_date` — the actual provenance. `review_date` must be a future
     date (a `VERIFIED` schedule whose review date has passed is treated as
     stale and rejected — see `CropStageSchedule.active_evidence`). Plan to
     refresh entries before they expire.
   - `status` — `"VERIFIED"` or `"SOURCED_PUBLIC_REFERENCE"` to go live (see
     above). Use `"UNVERIFIED"` or `"EXPERT_REVIEW_PENDING"` for drafts you
     want tracked but not yet live (they're counted by
     `CropStageRegistry.unverified_count` but never resolve for a farmer).
   - `reviewer` — a real agronomist's name/role for `VERIFIED`, or an honest
     description of who compiled/checked the sourced content (e.g. "AgrowAI
     content team — compiled from cited public source, not independently
     agronomist-reviewed") for `SOURCED_PUBLIC_REFERENCE`. Never fabricated.
   - `content_hash` — a SHA-256 of the entry's own content (everything except
     `content_hash` itself), used to detect accidental edits after review
     sign-off. **Don't hand-compute this.** Run:
     ```
     python scripts/compute_schedule_hash.py app/modules/calendar/data/verified_schedules/<crop_id>.json
     ```
     from the `backend/` directory — it validates the file against the
     schema and writes the correct `content_hash` in place.
3. Run the backend test suite (`pytest tests/test_calendar_registry.py
   tests/test_calendar_api_contract.py`) — once a real entry is present,
   `test_calendar_api_contract.py`'s `active_count == 0` assertion will need
   updating too; that's expected and is your signal the gate is now live for
   that crop.
4. Deploy. `ACTIVE_CROP_STAGE_REGISTRY` loads every `*.json` file in this
   directory at import time (see `_load_verified_schedule_entries()` in
   `registry.py`) — invalid or malformed files are skipped with a warning
   logged, not a startup crash, so a bad file can't take down the whole app,
   but it also means a typo silently leaves that crop unfixed. Check the
   deploy logs for `calendar.registry` warnings after every change here.

## What NOT to do

Don't wire the old `generate_events()` / `schedules.py` generic-template path
back in as a silent fallback for crops without a real entry — that was a
deliberate, discussed decision (see chat 2026-08-17): showing "not available"
is more honest than silently degrading to unreviewed, uncited generic advice
under the same UI as verified guidance. The `SOURCED_PUBLIC_REFERENCE` status
above (added 2026-08-17, same conversation) is the sanctioned way to show
real content without a full expert review — it still requires a genuine
citation and gets its own distinct, honestly-labeled UI treatment. It is not
a loophole for `schedules.py`'s uncited generic templates, which still must
never be wired in here.
