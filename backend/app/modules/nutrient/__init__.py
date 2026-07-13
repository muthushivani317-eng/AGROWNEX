"""Nutrient Deficiency AI module.

Identifies *visible* nutrient deficiencies from crop images and corroborates them
with the existing Soil, Satellite and Weather Intelligence signals. This is NOT
disease detection — it reasons about nutrition, and it never fabricates a
deficiency: when the evidence is insufficient it returns an honest "Not Confirmed"
and recommends a soil or tissue test (docs/PRODUCT_RULES.md).
"""
