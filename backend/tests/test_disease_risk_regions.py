from app.modules.disease_risk.regions import resolve_rule_region


def test_tamil_nadu_district_variants_resolve_to_state_rule_region() -> None:
    assert resolve_rule_region("Thanjavur") == "IN-TN"
    assert resolve_rule_region("  THIRUVANNAMALAI ") == "IN-TN"
    assert resolve_rule_region("Tiruchirappalli") == "IN-TN"
    assert resolve_rule_region("Kanchipuram") == "IN-TN"
    assert resolve_rule_region("Thanjavur District") == "IN-TN"


def test_missing_or_foreign_district_fails_closed() -> None:
    assert resolve_rule_region(None) is None
    assert resolve_rule_region("") is None
    assert resolve_rule_region("Mysuru") is None
    assert resolve_rule_region("Thanjavur123") is None
