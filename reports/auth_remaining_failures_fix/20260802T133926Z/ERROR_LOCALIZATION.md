# Error localization

Authentication errors now pass through an allowlisted localization mapper. Raw dotted keys and unknown provider/server strings are not rendered directly.

The observed backend HTTP 500 is displayed as:

`The authentication service is temporarily unavailable. Please try again later.`

The Tamil equivalent is retained as draft content requiring human product-language review. No unapproved translation is claimed as production-approved.
