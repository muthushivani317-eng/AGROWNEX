# Screenshot-driven screen audit

| Screen | Defect class | Root cause | Severity | Repair |
|---|---|---|---|---|
| Home | layout collapse, missing component styling | Grid/card geometry relied on NativeWind classes | Critical | Explicit two-column widths, card geometry, icon containers, spacing and light surface |
| AI Assistant | layout collapse, typography/spacing | Header, empty state and keyboard container relied on classes | High | Explicit header, 48dp controls, empty card geometry and keyboard behavior |
| Farm | contrast, overlapping filters, weak action | Mixed theme plus class-only list/filter/FAB styles | Critical | Forced light theme; explicit horizontal filters, list spacing and FAB |
| Profile | privacy, hierarchy, contrast | Full-number formatter and class-only cards | Critical | Masked number and explicit header/identity/section cards |
| Profile Setup | labels/chips/dropdown visibility | Class-only form gaps, rows, chips and dropdown field | Critical | Explicit form layout plus release-safe shared inputs/dropdowns/chips |
| Bottom tabs | mixed theme | Persisted system/dark preference selected incomplete dark palette | Critical | Deterministic light theme until full dark audit |
| Feature destinations | redirect loop | Authenticated non-auth routes were treated as invalid by startup guard | Critical | Guard now preserves legitimate authenticated stack routes |

Physical after-screens remain pending because the connected device is locked behind `NotificationShade`.
