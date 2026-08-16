# Laptop-off test

Status: `NOT_RUN_DEVICE_UNAVAILABLE`

The APK embeds its JavaScript and production Railway HTTPS URLs, so Metro is not
a packaging dependency. Actual reopening with ADB disconnected and the laptop
off remains a required supervised device test. Cached-login and fresh-OTP cases
must be recorded separately.
