# Firebase OTP test

Status: `PENDING_DEVICE_AND_AUTHORIZED_TEST_NUMBER`

Native Firebase App/Auth dependencies, Gradle integration, Firebase registrar,
providers, and generated resource names are present in the APK. This proves
packaging, not OTP operation.

No phone number was supplied and no device was visible to ADB. OTP request,
manual OTP verification, invalid-OTP behavior, Railway token exchange, and the
post-login screen were not tested. No bypass was used and no phone number was
logged.
