# Keyboard behavior

On device, a field tap produced `mInputShown=true` and an active `RemoteInputConnectionImpl` served by `ReactEditText`. The numeric phone keypad was visibly captured. One backspace reduced the value from ten digits to nine. Manual re-entry restored ten valid digits and enabled Send OTP. `adjustResize`, keyboard avoidance, and `keyboardShouldPersistTaps="handled"` kept the active controls reachable.
