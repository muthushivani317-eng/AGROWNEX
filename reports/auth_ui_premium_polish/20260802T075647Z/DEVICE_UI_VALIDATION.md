# Device UI validation

Device: connected Android handset `RZCY80YM62A`.

Validated from the newly bundled, installed standalone release APK:

- Login renders on a high-contrast light canvas.
- Logo is sharp at its bounded render size.
- Phone label, country prefix, input outline, and placeholder are visible.
- Disabled Send OTP is visibly a filled button.
- Continue with Google is visibly an outlined button.
- Terms and Privacy copy remains readable.
- Language screen is reachable by the registered deep link; its selector hierarchy and Continue action are present.

Not yet validated on-device:

- Genuine OTP screen, OTP error, and resend states require the operator to enter an owned test phone number and request a real Firebase OTP. No number was invented and no bypass was added.
- Automated ADB taps did not focus the phone input on this handset, so keyboard-resize acceptance remains pending manual interaction.

Screenshots are evidence only for the states actually reached. No OTP PASS is claimed without a real screen capture.
