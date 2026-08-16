# Design decisions

- Light, warm-neutral canvas (`#F6F9F6`) with white elevated cards and deep green branding.
- Native `StyleSheet` values for every critical surface so release visibility does not depend on NativeWind interoperability.
- 8-point spacing rhythm, 48–64 dp touch targets, 14–20 dp radii, and clear title/body hierarchy.
- Sharp brand presentation uses the high-resolution transparent icon source at a bounded size and renders the AgrowAI wordmark as native text.
- Phone prefix and input share one visible field with a focus ring and high-contrast entered text.
- Primary actions use filled green containers; federated sign-in uses an outlined secondary action.
- Errors use an accessible inline alert banner with icon, border, tinted background, and readable copy.
- OTP remains a single hidden native input for SMS autofill and full-code paste, projected into six visible cells for predictable backspace and focus behavior.
- Android keyboard avoidance uses `height`; iOS retains `padding`.
