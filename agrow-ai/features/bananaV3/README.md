# Banana V3 mobile integration

This feature is a presentation and transport layer over the frozen Banana V3
backend decision. It does not reproduce model preprocessing, thresholds, or
decision logic on the device. An `uncertain` response never exposes a candidate
disease.

Farmer-facing disease names and any future management wording must be verified
against an official source before release. This integration intentionally
contains no management advice, pesticide recommendation, commercial brand, or
payment flow.

Set `EXPO_PUBLIC_API_BASE_URL` to the deployed backend base URL. Production
release builds require HTTPS.
