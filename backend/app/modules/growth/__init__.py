"""Crop Growth Monitor module (docs/DATABASE_SCHEMA.md → Crop Growth,
docs/AI_PROMPTS.md → CROP GROWTH MONITOR PROMPT, docs/API_CONTRACT.md → CROP GROWTH).

Farmers upload crop photos over time and view the full growth history. The AI
analysis sits behind a ``GrowthAnalysisProvider`` abstraction so future models
(YOLO, nutrient-deficiency, pest, growth-stage) can replace Gemini with no change
to the service, API or frontend. Reuses the Disease Detection pipeline's image
quality gate, Cloudflare R2 storage, Gemini client shape and weather snapshot.
"""
