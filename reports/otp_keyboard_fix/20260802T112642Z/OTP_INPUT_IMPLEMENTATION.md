# OTP input implementation

One real native `TextInput` owns the six-digit value. It spans the complete OTP row, remains focusable and editable, uses `number-pad`/numeric input, supports SMS autofill and paste, filters non-digits, and caps input at six digits. The six boxes are a visual projection. Native text change owns backspace behavior, avoiding double deletion.
