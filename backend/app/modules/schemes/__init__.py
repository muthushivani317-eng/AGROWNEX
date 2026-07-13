"""Government Scheme Recommendation Engine (docs/DATABASE_SCHEMA.md → Government
domain, docs/AI_PROMPTS.md → GOVERNMENT SCHEME PROMPT, docs/API_CONTRACT.md → SCHEMES).

Not a listing app — an intelligent, deterministic **eligibility engine**. Verified
schemes are stored behind a ``GovernmentSchemeProvider`` abstraction (mock now;
Tamil Nadu / Central / Admin Portal / Scraper later) and matched against each
farmer's profile + farm to produce eligible schemes ranked by score
(docs/PRODUCT_RULES.md → schemes only from verified sources, never fabricated).
"""
