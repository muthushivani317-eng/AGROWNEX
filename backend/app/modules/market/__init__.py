"""Market Prices module (docs/API_CONTRACT.md → MARKET, docs/DATABASE_SCHEMA.md → Market).

Verified mandi prices for farmers. External price sources sit behind a
``MarketPriceProvider`` abstraction so the initial Open Government / Agmarknet
provider can later be replaced (eNAM, state APIs, local admin, paid feeds)
with no change to the service, API or frontend.
"""
