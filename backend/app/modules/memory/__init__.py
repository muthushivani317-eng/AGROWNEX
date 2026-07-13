"""Farm Memory Engine — AgrowAI's long-term agricultural memory (docs: AI Memory).

NOT a chat history. A structured, deterministic memory system that continuously
learns from a farm over months and years by reading structured events from every
existing module (Disease, Growth, Weather, Satellite, Soil, Nutrient, Schemes,
Market, Experts, AI Chat, Produce). The engine merges duplicate events, assigns
importance, generates seasonal/yearly summaries and links related memories — and
never fabricates history.

Designed so future vector search, embeddings, RAG and additional AI providers plug
in behind the same seam (``memory_embeddings`` reserved) with no redesign.
"""
