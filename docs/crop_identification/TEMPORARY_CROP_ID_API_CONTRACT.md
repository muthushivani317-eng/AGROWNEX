# Temporary crop-ID API contract

`POST /api/v1/crop-identification` accepts one JPEG, PNG, or WebP image and requires a controlled-tester bearer identity. It returns a strict versioned result with `request_id`, status, canonical nullable crop, localized display/reason containers, nullable self-reported confidence and source, mandatory-confirmation flag, provider/model/version, quality and temporary plant checks, and UTC timestamp.

`POST /api/v1/crop-identification/confirm` accepts `request_id`, one canonical `confirmed_crop`, and either `confirmed` or `farmer_selected_after_rejection`. It returns an opaque, expiring confirmation token. The token is not reusable for another actor, crop, or image.

The token must be submitted as multipart field `crop_confirmation_token` to a crop-specific disease endpoint. Missing, expired, cross-user, cross-crop, or image-mismatched receipts fail closed.

No response includes provider prompts, API keys, raw provider output, internal paths, model hashes, or raw confidence from a disease model.
