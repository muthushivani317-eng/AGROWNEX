"""Weather Intelligence module (docs/API_CONTRACT.md → WEATHER, PRODUCT_RULES 5).

Fetches forecasts from Open-Meteo for a farm's GPS coordinates, caches them, and
derives deterministic, rule-based agricultural insights (irrigation, spraying,
heat/rain/wind alerts, field work). This is the primary weather data source for
the Home Dashboard, AI Chat, Crop Calendar, Disease Detection and Notifications.
"""
