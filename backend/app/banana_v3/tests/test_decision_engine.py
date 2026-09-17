import numpy as np
from app.banana_v3.decision_engine import disease_decision, healthy_decision


def test_healthy_and_disease_use_predicted_class_policy():
    healthy = healthy_decision(np.array([10.0, 0.0]))
    assert healthy.predicted_class == "banana__healthy" and healthy.accepted
    disease = disease_decision(np.array([0.0, 0.0, 10.0]))
    assert disease.predicted_class == "banana__sigatoka_leaf_spot" and disease.accepted


def test_high_confidence_but_low_disease_margin_abstains():
    result = disease_decision(np.array([4.0, 3.9, -5.0]))
    assert result.predicted_class == "banana__cordana_leaf_spot"
    assert not result.accepted
