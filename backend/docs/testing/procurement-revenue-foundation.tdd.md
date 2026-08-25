# Procurement revenue foundation — TDD evidence

## Scope

This slice covers farmer-reported supply facts and the internal assisted-procurement workflow through `farmer_approval_pending`. Farmer acceptance, pickup, completed sales, payments, GMV, and earned commission are intentionally deferred until they can be backed by authenticated and immutable records.

## RED and GREEN evidence

| Stage | Evidence |
|---|---|
| Initial RED | `tests/test_procurement_revenue_slice.py` failed collection because `ProcurementCaseUpdateIn` did not exist. |
| Security hardening RED | 5 failures exposed provenance forgery, unsafe terminal statuses, missing buyer prerequisites, and invalid zero-price acceptance. |
| Lifecycle tightening RED | 4 failures exposed admin-controlled acceptance/pickup, unsafe legacy terminal normalization, and district-manager access. |
| Final GREEN | `pytest tests/test_procurement_revenue_slice.py tests/test_produce_flow.py tests/test_admin_flow.py -q` → `47 passed`. |
| Static checks | Scoped Ruff check → `All checks passed`. |
| Migration graph | `alembic heads` → `b91d0e6c4a32 (head)`. |
| SQLite migration | Isolated upgrade and downgrade against a real SQLite database → `SQLITE_SLICE_UP_DOWN_PASS`. |

## Guarantees

- Farmers can record cultivated area, expected total quantity, available sale quantity, and quality notes.
- Farmer writes are always labelled `farmer_reported`; verification cannot be self-asserted.
- Available quantity cannot exceed expected quantity, with API and database constraints.
- Legacy produce records and active legacy procurement states remain readable.
- The internal queue exposes enriched supply facts but masks buyer contact by default.
- Buyer-contact reveal is restricted to the dedicated procurement role and is target-audited.
- The internal workflow has one authoritative case state and accepts safe legacy status aliases.
- Retired legacy sale/collection transitions fail explicitly rather than fabricating completion.
- Phase 1 ends at farmer approval pending; no earned revenue is calculated or reported.
- Buyer offer price, transport cost, and commission rate use decimal database types and bounded validation.

## Known pre-deployment work

- Run migration upgrade/downgrade against the production PostgreSQL version.
- Add the farmer-authenticated acceptance and immutable frozen-offer slice before advancing beyond approval pending.
- Add transaction, payment, reversal, and commission ledgers before reporting GMV or revenue.
- Add organizational/district scopes if procurement access is later delegated beyond the dedicated central procurement team.
