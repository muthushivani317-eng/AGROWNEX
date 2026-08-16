# Translation Key Audit

- Added the missing `farm.selectDate` key in English; Tamil currently uses the same safe English fallback rather than an invented translation.
- i18next now returns `Content unavailable` when neither Tamil nor English contains a requested key, so dotted internal keys are not rendered.
- Removed `HUMAN_TRANSLATION_REVIEW_REQUIRED` from Disease and Plant Identifier farmer UI.
- Removed `TAMIL_TRANSLATION_REVIEW_REQUIRED` from recommendation rendering; verified English source text is the fallback until Tamil is human reviewed.
- Internal workflow enum strings remain in typed state machines and tests; those are not farmer-facing copy.

Static release-UI result: `PASS_WITH_HUMAN_TAMIL_REVIEW_REMAINING`. Physical result: `NOT_RUN`.
