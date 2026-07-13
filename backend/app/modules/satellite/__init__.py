"""Satellite Intelligence — professional farm monitoring over free Sentinel-2.

A deterministic Satellite Engine computes standard vegetation indices (NDVI, NDRE,
EVI, NDMI) and classifies vegetation health / stress / moisture, with a provider
abstraction so commercial sources (Sentinel Hub, Copernicus, Planet, Maxar, Earth
Engine, Azure Planetary Computer, drone/thermal/hyperspectral) can replace or
complement Sentinel with no frontend change. Imagery is never fabricated — when a
scene is unavailable (cloud, delay, provider issue, or no farm polygon) the session
is an honest "Not Available". Reuses auth, the farm repository + polygon, the
weather context (optional), the notification engine, the response envelope and
localization.
"""
