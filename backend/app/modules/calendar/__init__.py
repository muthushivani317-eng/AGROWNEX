"""Crop Calendar module (docs/API_CONTRACT.md → CROP SESSION / calendar).

Deterministic, rule-based farming schedule generated from predefined crop
templates + the farm's sowing date (no AI in V1). At read time it reuses the
Weather module's insights to add weather advisories (delay irrigation on heavy
rain, delay spraying on strong wind, recommend irrigation in extreme heat) —
without duplicating any weather logic. Providers are abstracted so future AI can
adjust schedules without any frontend change.
"""
