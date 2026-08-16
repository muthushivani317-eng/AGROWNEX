# AgrowAI Documentation Master Index

Updated: 2026-08-07

This index is the starting point for understanding the entire AgrowAI application. The workspace currently contains **785 Markdown files** in the principal documentation/evidence locations. They are not all equally authoritative: some describe the current application, some preserve historical repair work, and many autonomous-pipeline phase files are short evidence placeholders.

## Recommended reading order

1. [Complete Technical Audit](./AGROWAI_COMPLETE_TECHNICAL_AUDIT.md) — current high-level technical truth: architecture, features, models, APIs, databases, security, gaps and priorities.
2. [Master Product Specification](../agrow-ai/docs/AGROWAI_MASTER_SPEC.md) — intended product behavior and scope.
3. [Frontend Architecture](../agrow-ai/docs/FRONTEND_ARCHITECTURE.md) — Expo/React Native client structure.
4. [Backend Architecture](../agrow-ai/docs/BACKEND_ARCHITECTURE.md) — FastAPI service layering and modules.
5. [Database Schema](../agrow-ai/docs/DATABASE_SCHEMA.md) — remote data model and relationships.
6. [API Contract](../agrow-ai/docs/API_CONTRACT.md) — mobile/backend request and response boundaries.
7. [User Flows](../agrow-ai/docs/USER_FLOWS.md) — navigation and farmer journeys.
8. [AI Decision Matrix](../agrow-ai/docs/AI_DECISION_MATRIX.md) — model/provider routing decisions.
9. [AI Prompts](../agrow-ai/docs/AI_PROMPTS.md) — Gemini prompt and safety behavior.
10. [Security](../agrow-ai/docs/SECURITY.md) — authentication, configuration and application security.
11. [Product Rules](../agrow-ai/docs/PRODUCT_RULES.md) — non-negotiable product rules.
12. [Deployment](../agrow-ai/docs/DEPLOYMENT.md) — backend/mobile delivery design.

## Current audit and security evidence

These files were produced or updated during the latest internal-testing and security work:

- [Complete Technical Audit](./AGROWAI_COMPLETE_TECHNICAL_AUDIT.md)
- [Feature Audit](./internal_testing/FEATURE_AUDIT.md)
- [APK Inspection](./internal_testing/APK_INSPECTION.md)
- [APK String Provenance](./internal_testing/APK_STRING_PROVENANCE.md)
- [Dependency Security Review](./internal_testing/DEPENDENCY_SECURITY_REVIEW.md)

Related machine-readable evidence is beside these documents as JSON, and complete test/build logs are under `artifacts/internal_testing/logs/`.

## Canonical application documentation

All 15 current mobile/product documents are under [`agrow-ai/docs`](../agrow-ai/docs/):

- [AGROWAI_MASTER_SPEC.md](../agrow-ai/docs/AGROWAI_MASTER_SPEC.md)
- [AI_DECISION_MATRIX.md](../agrow-ai/docs/AI_DECISION_MATRIX.md)
- [AI_PROMPTS.md](../agrow-ai/docs/AI_PROMPTS.md)
- [API_CONTRACT.md](../agrow-ai/docs/API_CONTRACT.md)
- [BACKEND_ARCHITECTURE.md](../agrow-ai/docs/BACKEND_ARCHITECTURE.md)
- [CODING_STANDARDS.md](../agrow-ai/docs/CODING_STANDARDS.md)
- [COMPONENT_LIBRARY.md](../agrow-ai/docs/COMPONENT_LIBRARY.md)
- [DATABASE_SCHEMA.md](../agrow-ai/docs/DATABASE_SCHEMA.md)
- [DEPLOYMENT.md](../agrow-ai/docs/DEPLOYMENT.md)
- [DESIGN_SYSTEM.md](../agrow-ai/docs/DESIGN_SYSTEM.md)
- [FIREBASE_PHONE_AUTH_PRODUCTION_CHECKLIST.md](../agrow-ai/docs/FIREBASE_PHONE_AUTH_PRODUCTION_CHECKLIST.md)
- [FRONTEND_ARCHITECTURE.md](../agrow-ai/docs/FRONTEND_ARCHITECTURE.md)
- [PRODUCT_RULES.md](../agrow-ai/docs/PRODUCT_RULES.md)
- [SECURITY.md](../agrow-ai/docs/SECURITY.md)
- [USER_FLOWS.md](../agrow-ai/docs/USER_FLOWS.md)

The backend also has two documents in [`backend/docs`](../backend/docs/). They should be read as backend-specific supplements.

## Historical implementation and repair reports

There are **114 Markdown reports** under [`reports`](../reports/). These preserve what was inspected, changed, tested or blocked at specific moments. They are historical evidence, not always the current state.

The most useful report sets are:

- [`full_app_release_blocker_audit/20260802T185705Z`](../reports/full_app_release_blocker_audit/20260802T185705Z/) — feature inventory, route matrix, API matrix, UI, disease, AI chat, plant identifier and release blockers.
- [`crop_identification_controlled_beta_audit/20260803T193824Z`](../reports/crop_identification_controlled_beta_audit/20260803T193824Z/) — crop-identification controlled-beta audit and final report.
- [`crop_id_recommendation_full_execution/20260801T114135Z`](../reports/crop_id_recommendation_full_execution/20260801T114135Z/) — model, dataset, calibration, security, recommendation and deployment evidence.
- [`standalone_android_release/20260801T182359Z`](../reports/standalone_android_release/20260801T182359Z/) — APK inspection, release validation, OTP and laptop-off evidence.
- [`standalone_startup_ui_fix/20260801T193856Z`](../reports/standalone_startup_ui_fix/20260801T193856Z/) — startup state, splash and route audits.
- [`standalone_real_device_ui_fix/20260802T072202Z`](../reports/standalone_real_device_ui_fix/20260802T072202Z/) — real-device UI repair evidence.
- [`authenticated_app_ui_navigation_fix/20260802T184151Z`](../reports/authenticated_app_ui_navigation_fix/20260802T184151Z/) — authenticated navigation and screen audit.
- [`backend_auth_500_fix/20260802T175205Z`](../reports/backend_auth_500_fix/20260802T175205Z/) — backend authentication/database failure analysis.
- [`auth_remaining_failures_fix/20260802T133926Z`](../reports/auth_remaining_failures_fix/20260802T133926Z/) — remaining authentication repairs.
- [`auth_ui_premium_polish/20260802T075647Z`](../reports/auth_ui_premium_polish/20260802T075647Z/) — authentication UI work.
- [`phone_input_keyboard_fix/20260802T111706Z`](../reports/phone_input_keyboard_fix/20260802T111706Z/) and [`otp_keyboard_fix/20260802T112642Z`](../reports/otp_keyboard_fix/20260802T112642Z/) — phone/OTP behavior.
- [`crop_id_data_acquisition_and_review/20260801T124423Z`](../reports/crop_id_data_acquisition_and_review/20260801T124423Z/) and [`crop_id_human_review_and_collection_setup/20260801T125439Z`](../reports/crop_id_human_review_and_collection_setup/20260801T125439Z/) — dataset licensing, collection and human review.

When a historical report conflicts with the Complete Technical Audit or current source code, prefer the current source and latest audit.

## Autonomous pipeline evidence

There are **397 Markdown files** under [`agrowai_autonomous_pipeline/EVIDENCE`](../agrowai_autonomous_pipeline/EVIDENCE/). This is the complete phase-by-phase evidence tree for repository audit, crop registry, datasets, licensing, provenance, validation, leakage control, training/runtime gates, recommendations and release validation.

Use each phase's `phase_summary.md` first. Then read its substantive audit/report documents. Files named `changed_files.md`, `blockers.md` and `next_actions.md` are often short pipeline bookkeeping records and may not contain detailed analysis.

Important founder-test evidence is under [`FOUNDER_TEST_FOUNDATION`](../agrowai_autonomous_pipeline/EVIDENCE/FOUNDER_TEST_FOUNDATION/), including the storage inventory report and its JSON companion.

## Additional root documentation

There are **252 Markdown files** under [`docs`](../docs/). This area contains model/dataset/recommendation research and execution documentation accumulated across the project. Treat signed/frozen artifact manifests and latest timestamped reports as stronger evidence than planning notes.

## Document inventory totals

| Location | Markdown files | Approximate content size | Meaning |
|---|---:|---:|---|
| `artifacts/` | 5 | 37.7 KB | Latest audit/security outputs |
| `agrow-ai/docs/` | 15 | 108.9 KB | Canonical application documentation |
| `backend/docs/` | 2 | 9.4 KB | Backend supplements |
| `reports/` | 114 | 120.9 KB | Historical implementation/repair evidence |
| `docs/` | 252 | 261.7 KB | Research, model, recommendation and execution documentation |
| `agrowai_autonomous_pipeline/EVIDENCE/` | 397 | 271.1 KB | Phase-by-phase autonomous pipeline evidence |
| **Total** | **785** | **about 810 KB** | Complete principal Markdown knowledge set |

## How to interpret status language

- **Implemented** means executable code exists; it does not automatically mean field-validated or production-ready.
- **Integrated** means a path is wired into an API/application route; external configuration may still be required.
- **Restricted/internal** means the code or model must not be presented as a general farmer production capability.
- **Scaffolded** means types, screens, settings or provider interfaces exist, but the real external behavior is absent.
- **Historical PASS** proves a command passed at the report timestamp, not that every later workspace edit preserves it.
- Agricultural recommendation documents remain subject to official-source verification and reviewer approval.

## Fastest path to “know everything”

Read the Complete Technical Audit, then the 15 canonical app documents, then the latest security evidence. Use the historical report folders only when you need the detailed history of a particular feature or defect. Use autonomous-pipeline evidence when auditing datasets, model provenance, crop safety gates or recommendation verification.
