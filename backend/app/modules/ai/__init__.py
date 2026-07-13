"""AI Chat module (docs/API_CONTRACT.md → AI CHAT, docs/AI_PROMPTS.md).

A conversational assistant for farmers. Every request flows through an AI router
pipeline (context/farm-memory → prompt → model → safety validation → persist),
uses Google Gemini as the single provider, and defaults to simple Tamil. API keys
never leave the backend (docs/SECURITY.md → AI security).
"""
