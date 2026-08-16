# Unresolved blockers

- Android keyguard/Always On Display remains active. `NotificationShade` owns current focus and `UI_HIERARCHY_AFTER.xml` contains only `com.android.systemui` nodes.
- Therefore screenshots cannot yet prove language, login, Send OTP, or OTP-entry visibility.
- No real OTP was requested or entered.
- The original before screenshot is byte-corrupted and cannot be rendered; the original before UI hierarchy remains valid evidence.
- Two high and thirteen moderate advisories exist in the pre-existing dependency graph. No automatic or breaking audit fix was applied.
