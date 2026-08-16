# Phone input implementation

- A visible native `TextInput` remains authoritative.
- `editable`, `showSoftInputOnFocus`, `keyboardType="phone-pad"`, and `inputMode="tel"` are explicit.
- The field has non-zero dimensions, visible text, cursor, `+91` prefix, and native focus border.
- Tapping the prefix, blank field space, or input invokes the native input ref.
- Input is sanitized to digits and ten national digits; pasted `+91` input is supported.
- Firebase receives only the existing normalized E.164 value.
- Send OTP remains gated by the existing schema and pending state.
