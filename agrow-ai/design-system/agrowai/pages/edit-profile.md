# Edit Profile Page Overrides

> **PROJECT:** AgrowAI
> **Generated:** 2026-08-23 03:07:15
> **Page Type:** Settings / Profile

> ⚠️ **IMPORTANT:** Rules in this file **override** the Master file (`design-system/MASTER.md`).
> Only deviations from the Master are documented here. For all other rules, refer to the Master.

---

## Page-Specific Rules

### Layout Overrides

- **Max Width:** 1200px (standard)
- **Layout:** Full-width sections, centered content

### Spacing Overrides

- No overrides — use Master spacing

### Typography Overrides

- No overrides — use Master typography

### Color Overrides

- No overrides — use Master colors

### Component Overrides

- Avoid: Use a clickable div or reveal the only action on hover
- Avoid: Single row actions only
- Avoid: No feedback after submit

---

## Page-Specific Components

- No unique components for this page

---

## Recommendations

- Effects: Tonal elevation (overlay colors instead of strong shadows), pill-shaped buttons and chips (borderRadius 999), emphasized easing Easing.bezier(0.2,0,0,1), state layers (pressed overlays 10–15% opacity), Reanimated-filled label float for inputs, HapticFeedback on FAB/toggles
- Accessibility: Prefer a button and expose pressed or selected state that matches the visible label
- Data Entry: Allow multi-select and bulk edit
- Forms: Show loading then success/error state
