from __future__ import annotations

from collections import Counter

from scripts.prepare_four_crop_identity_training import (
    CLASSES,
    SPLITS,
    audit_split,
    grouped_split,
)


def rows() -> list[dict[str, object]]:
    result = []
    for crop in CLASSES:
        for index in range(40):
            result.append(
                {
                    "sha256": f"{crop}-{index}",
                    "crop_class": crop,
                    "source_family_id": f"{crop}-family-{index // 2}",
                }
            )
    return result


def test_grouped_split_is_deterministic_and_complete():
    first = grouped_split(rows(), seed=123)
    second = grouped_split(rows(), seed=123)
    assert first == second
    assert {row["split"] for row in first} == set(SPLITS)
    for split in SPLITS:
        assert {row["crop_class"] for row in first if row["split"] == split} == set(CLASSES)


def test_family_never_crosses_splits():
    assigned = grouped_split(rows(), seed=123)
    families: dict[str, set[str]] = {}
    for row in assigned:
        families.setdefault(str(row["source_family_id"]), set()).add(str(row["split"]))
    assert all(len(splits) == 1 for splits in families.values())


def test_reserved_and_sha_leakage_fail_closed():
    assigned = grouped_split(rows(), seed=123)
    clean = audit_split(assigned, set())
    assert clean["split_integrity"] == "PASS"
    assert clean["family_leakage"] == 0
    assert clean["sha_leakage"] == 0
    assert clean["reserved_leakage"] == 0
    reserved = audit_split(assigned, {str(assigned[0]["sha256"])})
    assert reserved["split_integrity"] == "FAIL"


def test_natural_split_preserves_all_rows():
    assigned = grouped_split(rows(), seed=123)
    assert len(assigned) == len(rows())
    assert Counter(row["crop_class"] for row in assigned) == Counter(
        row["crop_class"] for row in rows()
    )
