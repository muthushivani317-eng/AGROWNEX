from __future__ import annotations

import math
from typing import Mapping


def decide(
    probabilities: list[float],
    class_names: list[str],
    class_thresholds: Mapping[str, float],
    fallback_threshold: float,
    margin_threshold: float,
    entropy_threshold: float,
) -> dict[str, object]:
    ranked = sorted(range(len(probabilities)), key=probabilities.__getitem__, reverse=True)
    top1, top2 = ranked[:2]
    crop = class_names[top1]
    confidence = probabilities[top1]
    margin = confidence - probabilities[top2]
    entropy = -sum(value * math.log(max(value, 1e-12)) for value in probabilities)
    threshold = class_thresholds.get(crop, fallback_threshold)
    accepted = (
        confidence >= threshold
        and margin >= margin_threshold
        and entropy <= entropy_threshold
    )
    return {
        "predicted_crop": crop,
        "accepted": accepted,
        "confidence": confidence,
        "margin": margin,
        "entropy": entropy,
        "reason_code": "CROP_MATCH" if accepted else "CROP_IDENTITY_UNCERTAIN",
    }
