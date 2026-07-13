"""Nutrient vision prompts (docs/AI_PROMPTS.md → Leaf analysis; Safety rules).

The model acts as a crop-nutrition specialist. It must only report a deficiency it
can actually see, state uncertainty, and never fabricate. When the leaf is
inconclusive it returns ``primary_deficiency: null`` — the engine then reports an
honest "not confirmed" and recommends a soil/tissue test.
"""
from __future__ import annotations

NUTRIENT_SYSTEM_PROMPT = (
    "You are AgrowAI's crop-nutrition specialist for Indian farmers. You analyse a "
    "single crop-leaf photo for VISIBLE nutrient-deficiency symptoms. This is NOT "
    "disease detection — focus on nutrition (colour, veins, interveinal chlorosis, "
    "leaf edges/tips, necrosis, purpling, curl, leaf size, and whether older or "
    "younger leaves are affected first).\n"
    "Rules:\n"
    "- Never invent a deficiency. If symptoms are unclear or could be many causes, "
    "set primary_deficiency to null and lower confidence.\n"
    "- Prefer null over a guess. A soil or tissue test is the ground truth.\n"
    "- Only use these nutrient names: nitrogen, phosphorus, potassium, sulphur, "
    "calcium, magnesium, iron, zinc, boron, copper, manganese, molybdenum, chlorine.\n"
    "- Respond ONLY with a single JSON object. No markdown, no extra text."
)

_SYMPTOM_VOCAB = (
    "yellowing, interveinal_chlorosis, vein_yellowing, purpling, leaf_edge_scorch, "
    "leaf_tip_necrosis, necrosis, spots, leaf_curl, stunted_leaf, pale_leaf, "
    "older_leaf_first, younger_leaf_first, deformed_growth"
)


def build_nutrient_prompt(crop: str | None, language: str, farm_context: str) -> str:
    """Build the per-request nutrient-analysis prompt."""
    lang_name = "Tamil" if language == "ta" else "English"
    crop_line = f"The crop is likely {crop}." if crop else "Identify the crop if you can."
    return (
        f"{crop_line}\n"
        f"{farm_context}\n\n"
        "Analyse the leaf photo for nutrient-deficiency symptoms and return this JSON:\n"
        "{\n"
        '  "plant_present": true/false,\n'
        '  "reject_reason": null or one of human/animal/building/soil/sky/other,\n'
        '  "crop": "<crop or unknown>",\n'
        f'  "visible_symptoms": [subset of: {_SYMPTOM_VOCAB}],\n'
        '  "primary_deficiency": "<nutrient>" or null,\n'
        '  "secondary_deficiency": "<nutrient>" or null,\n'
        '  "confidence": 0-100,\n'
        '  "severity": "none|mild|moderate|severe",\n'
        '  "affected_area": "none|spots|patches|scattered|widespread|whole_field",\n'
        '  "explanation_tamil": "<2 short sentences in simple Tamil>",\n'
        '  "explanation_english": "<2 short sentences in English>"\n'
        "}\n"
        f"Write the explanation for the farmer in simple {lang_name}. "
        "If you are not confident, say so and set primary_deficiency to null."
    )
