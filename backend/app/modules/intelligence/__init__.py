"""Crop Intelligence Engine — the central intelligence layer of AgrowAI.

This module does NOT perform detection itself. It aggregates the outputs of every
agricultural module (Disease, Nutrient, Soil, Satellite, Weather, Growth, Calendar,
Expert) into a single farm-health assessment: per-module health sub-scores, an
overall health score, a risk level, and prioritized generic recommendations.

Missing modules never invent values — they reduce confidence (docs/PRODUCT_RULES.md).
Every future AI model (YOLO, Vision Transformer, Yield Prediction, AI Memory) plugs
in behind the same signal/engine seam with no redesign.
"""
