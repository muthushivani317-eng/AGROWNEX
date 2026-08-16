from app.disease_recommendations.registry import CHEMICAL_WITHHELD, LABELS, get_recommendation

def test_every_runtime_label_has_exactly_one_safe_mapping():
    assert len(LABELS) == 20
    for label, (crop, *_rest) in LABELS.items():
        result = get_recommendation(crop, label, diagnosis_accepted=True)
        assert result["runtime_label"] == label
        assert result["chemical_recommendation_status"] == CHEMICAL_WITHHELD

def test_unknown_and_cross_crop_labels_fail_closed():
    assert get_recommendation("paddy", "unknown", diagnosis_accepted=True)["outcome"] == "RUNTIME_LABEL_UNMAPPED"
    assert get_recommendation("cotton", "rice_blast", diagnosis_accepted=True)["outcome"] == "RUNTIME_LABEL_UNMAPPED"

def test_uncertain_and_restricted_results_do_not_offer_chemicals():
    uncertain = get_recommendation("paddy", "rice_blast", diagnosis_accepted=False)
    restricted = get_recommendation("chilli", "chilli__bacterial_spot", diagnosis_accepted=True)
    assert uncertain["outcome"] == "DIAGNOSIS_UNCERTAIN"
    assert restricted["outcome"] == "RECOMMENDATION_NOT_VERIFIED"

def test_controlled_test_restricted_result_gets_partial_nonchemical_guidance():
    result = get_recommendation(
        "chilli",
        "chilli__bacterial_spot",
        diagnosis_accepted=True,
        controlled_test=True,
    )
    assert result["outcome"] == "RECOMMENDATION_PARTIAL"
    assert result["chemical_options"] == []
    assert result["chemical_recommendation_status"] == CHEMICAL_WITHHELD
