"""Sell My Produce — Procurement Intelligence (docs/DATABASE_SCHEMA.md → Produce
domain, docs/API_CONTRACT.md → PRODUCE, docs/USER_FLOWS.md → SELL MY PRODUCE).

This is **not a marketplace**. Farmers do not sell directly inside the app and no
transactions happen here. The module collects verified future-harvest information
so it can be routed to procurement channels later. Harvest offers are stored
behind a ``ProduceProvider`` abstraction (mock now; eNAM / FPO / private buyers /
export companies / admin portal later) and enriched by a deterministic
**Procurement Engine** that never fabricates market prices or buyers
(docs/PRODUCT_RULES.md → market data only from verified sources).
"""
