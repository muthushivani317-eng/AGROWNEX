"""Disease Detection module (docs/API_CONTRACT.md → DISEASE, docs/AI_PROMPTS.md).

Farmer photo → image-quality gate → Gemini Vision analysis → structured disease
report (crop, disease, confidence, severity, symptoms, causes, recommendations,
prevention, Tamil explanation) → image stored in Cloudflare R2 + metadata in
PostgreSQL. Gemini is the single V1 provider, isolated behind a small interface
so future providers can replace it without frontend changes.
"""
