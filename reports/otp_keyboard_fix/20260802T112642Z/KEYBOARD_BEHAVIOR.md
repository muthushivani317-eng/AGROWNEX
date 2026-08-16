# Keyboard behavior

The OTP screen opened with an active native input connection and visible numeric keypad. After hiding the keyboard, tapping the OTP row reopened it (`mInputShown=true`). Six manually entered digits enabled Verify. Backspace reduced the value to five and restoration returned it to six. `adjustResize` kept Verify visible above the keypad.
