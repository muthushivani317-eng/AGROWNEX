"""Pure deterministic hierarchy over frozen logits and policy values."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .config import (
    DISEASE_CLASSES,
    DISEASE_TEMPERATURE,
    DISEASE_THRESHOLDS,
    HEALTHY_CLASSES,
    HEALTHY_TEMPERATURE,
    HEALTHY_THRESHOLDS,
)
from .error_codes import DecisionCode


@dataclass(frozen=True)
class StageDecision:
    predicted_class: str
    confidence: float
    margin: float
    accepted: bool


def calibrated_decision(
    logits: np.ndarray, classes: dict[str, int], temperature: float, thresholds: dict
) -> StageDecision:
    values = np.asarray(logits, dtype=np.float64).reshape(-1) / temperature
    values -= values.max()
    probabilities = np.exp(values)
    probabilities /= probabilities.sum()
    order = np.argsort(probabilities)
    top = int(order[-1])
    confidence = float(probabilities[top])
    margin = confidence - float(probabilities[order[-2]])
    inverse = {index: name for name, index in classes.items()}
    predicted = inverse[top]
    policy = thresholds[predicted]
    return StageDecision(
        predicted, confidence, margin,
        confidence >= policy["confidence"] and margin >= policy["margin"],
    )


def healthy_decision(logits: np.ndarray) -> StageDecision:
    return calibrated_decision(logits, HEALTHY_CLASSES, HEALTHY_TEMPERATURE, HEALTHY_THRESHOLDS)


def disease_decision(logits: np.ndarray) -> StageDecision:
    return calibrated_decision(
        logits, DISEASE_CLASSES, DISEASE_TEMPERATURE, DISEASE_THRESHOLDS
    )


def accepted_code(class_id: str) -> DecisionCode:
    return {
        "banana__healthy": DecisionCode.BV3_HEALTHY_ACCEPTED,
        "banana__cordana_leaf_spot": DecisionCode.BV3_CORDANA_ACCEPTED,
        "banana__pestalotiopsis_leaf_spot": DecisionCode.BV3_PESTALOTIOPSIS_ACCEPTED,
        "banana__sigatoka_leaf_spot": DecisionCode.BV3_SIGATOKA_ACCEPTED,
    }[class_id]
