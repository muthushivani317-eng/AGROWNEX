# Crop Calendar / Disease Risk -- real content integration (2026-08-18)

## What's live now

Two of the 11 supported crops now have real, source-cited, hash-validated
content committed directly into the AgrowAi_app repo (D:\AgrowAI\AgrowAi_app):

**Crop Calendar** (`backend/app/modules/calendar/data/verified_schedules/`):
- `paddy.json` -- 7 stages, 14 activities, TNAU Agritech Portal (Crop
  Production Guide 2020, rice section). status=SOURCED_PUBLIC_REFERENCE.
- `chilli.json` -- 6 stages, 9 activities, TNAU Agritech Portal (Chilli
  cultural practices/yield) + ICAR-CCARI Decision Support System.
  status=SOURCED_PUBLIC_REFERENCE.

**Disease Risk** (`backend/app/modules/disease_risk/data/rule_packs/`):
- `paddy_sheath_blight.json` -- 28-32C + humidity >=96% during
  tillering/panicle-initiation/booting-heading-flowering. TNAU rice_6.html.
- `paddy_bacterial_leaf_blight.json` -- 25-30C during nursery/early
  transplanting. TNAU rice_3.html.
- `chilli_damping_off.json` -- <=22C + humidity >=90% during nursery.
  TNAU chilli_diseases_1.html.

All five files were validated against byte-identical copies of the repo's
own pydantic models (`CropStageSchedule`, `RulePack`) and hashed with logic
copied verbatim from `schedule_hash()` / `RulePack.expected_hash()`, using
the exact pydantic version pinned in `backend/requirements.txt` (2.10.4).
`content_hash` in each committed file is real and will validate against the
actual `scripts/compute_schedule_hash.py` / `scripts/compute_rule_pack_hash.py`
without needing to be regenerated -- but it's cheap and worth re-running
those scripts once, from the repo, to be 100% sure (see "Please verify"
below).

**i18n**: added `calendar.stages.*`, `calendar.verified.paddy.*`,
`calendar.verified.chilli.*`, and `diseaseRisk.verified.*` keys to both
`agrow-ai/localization/locales/en.ts` and `ta.ts` (Tamil translations
included). Both files pass `tsc --noEmit` syntax checking.

**Tests updated** (both edits are deliberate consequences of adding live
content, not incidental changes):
- `backend/tests/test_calendar_api_contract.py` --
  `test_production_registry_contains_no_claimed_verified_agronomy` now
  asserts `active_count == 2` (was 0), with a comment explaining why.
- `backend/tests/test_disease_risk_api_contract.py` --
  `test_no_verified_rule_is_persisted_idempotently_and_owner_scoped` now
  creates its test farm with `crop="redgram"` instead of `"paddy"`, since
  paddy now has live rule packs and would no longer hit
  `RULE_PACK_UNAVAILABLE` in that test. Comment explains why.

## Please verify

I could not run the actual `pytest` suite from this session (no access to
the full backend environment/DB). Before deploying, please run, from
`backend/`:

```
python scripts/compute_schedule_hash.py app/modules/calendar/data/verified_schedules/paddy.json
python scripts/compute_schedule_hash.py app/modules/calendar/data/verified_schedules/chilli.json
python scripts/compute_rule_pack_hash.py app/modules/disease_risk/data/rule_packs/paddy_sheath_blight.json
python scripts/compute_rule_pack_hash.py app/modules/disease_risk/data/rule_packs/paddy_bacterial_leaf_blight.json
python scripts/compute_rule_pack_hash.py app/modules/disease_risk/data/rule_packs/chilli_damping_off.json
pytest tests/test_calendar_registry.py tests/test_calendar_registry_loader.py tests/test_calendar_api_contract.py tests/test_disease_risk_engine.py tests/test_disease_risk_registry_loader.py tests/test_disease_risk_api_contract.py
```

The hash scripts should report "no change" (or write the same hash back) if
everything lines up; if pytest fails anywhere, that's a real signal to look
at before this goes live, not something to silently override.

## What's NOT done yet (9 of 11 crops)

redgram, cotton, groundnut, coconut, blackgram, maize, pearl millet,
greengram, banana still have no live calendar or disease-risk entry. I have
usable raw source material for several of them already (from earlier
research) -- cotton (bacterial blight, temp+humidity), maize (downy mildew),
pearl millet (downy mildew + ergot) all have quantified thresholds ready to
convert into rule packs the same way paddy/chilli were done. The pattern is
now proven end-to-end; extending it is mechanical repetition of this same
process per crop.

## Why only 2 crops, not all 11, this round

The actual repo schema turned out far stricter than my first pass (which was
built without repo access): calendar needs per-activity day-level tasks
wired to real i18n keys, not just broad growth-stage windows; disease risk
needs concrete numeric thresholds with comparison operators, one rule pack
per crop+disease, matched against calendar stage codes, plus a content_hash
computed the exact way the repo computes it. Doing this correctly for 2
crops and proving the whole pipeline (schema, hashing, i18n, test updates)
end-to-end was safer than doing a shallow, error-prone pass across all 11.
