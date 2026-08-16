# Crop Calendar completion evidence

## Safety boundary

- Production active verified registry entries: `0`.
- Registered unverified/pending entries: `0`.
- `backend/app/modules/calendar/schedules.py`: `LEGACY_UNUSED`; referenced only by the legacy pure generator and tests, never by `CalendarService`.
- `agrow-ai/features/calendar/services/schedules.ts`: `PRODUCTION_UNVERIFIED_DISABLED`; `getSchedule` always returns an empty list, so the local provider cannot generate agronomic tasks.
- Persisted tasks are returned and notified only while their verified registry version and content hash remain active.

## RED evidence

- Backend calendar tests initially failed at collection because the farm-context mismatch guard did not exist.
- Mobile provider tests initially failed because verification provenance was not mapped and an API outage did not return visibly cached data.

## GREEN evidence

- Backend focused calendar/notification suite: 66 passed.
- Mobile focused calendar/Home/notification suite: 28 passed.
- TypeScript, scoped Ruff, and scoped Prettier checks passed.

No agricultural schedule was activated or added. Agricultural content remains unavailable until a provenance-bound verified pack is installed.
