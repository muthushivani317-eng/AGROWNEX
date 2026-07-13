"""Soil Intelligence — location + farmer-report soil insights (future-ready).

A deterministic Soil Engine classifies farmer-provided (or future lab / government
/ satellite / Gemini-OCR) soil values against standard Soil Health Card bands and
produces *generic* agronomic advice only — never a commercial fertilizer brand,
never a fabricated value (docs/PRODUCT_RULES.md). Reuses auth, the farm repository,
the upload service (report images), the notification engine (soil events), the
response envelope and localization.
"""
