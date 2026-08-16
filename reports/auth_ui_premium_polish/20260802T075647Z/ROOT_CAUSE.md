# Root cause

The standalone release did not reliably resolve critical NativeWind classes on the authentication surfaces. Layout, borders, fills, and text contrast therefore depended on styles that were absent or overridden in the bundled APK. The system dark appearance made the failure especially severe: dark text and transparent controls rendered on a black surface.

The login wordmark also used a large raster composite scaled across the screen. It appeared soft and contained more detail than the available display size could reproduce.

The fix makes critical auth visibility native-style authoritative. It uses an explicit light authentication canvas, native card/input/button/OTP-cell styling, a compact high-resolution icon plus native wordmark, and structured error presentation. Firebase actions, validation, resend timing, and authentication policy were not changed.
