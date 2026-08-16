from __future__ import annotations

from scripts.audit_crop_identity_dataset_approval import (
    approval_for,
    classify_originality,
    dataset_decision,
    manifest_hash,
)


def test_original_requires_manifest_and_registry_evidence():
    row = {"original_or_augmented": "ORIGINAL"}
    source = {"image_origin": "CLEANED ORIGINAL IMAGES"}
    assert classify_originality(row, source) == "ORIGINAL_VERIFIED"
    assert (
        classify_originality(row, {"image_origin": "unknown"})
        == "UNKNOWN_ORIGINALITY"
    )


def test_reserved_material_is_never_approved():
    status, approved, _, reasons, _ = approval_for(
        archive_verified=True,
        extraction_verified=True,
        originality="ORIGINAL_VERIFIED",
        crop_identity="CROP_IDENTITY_VERIFIED_FROM_SOURCE",
        licence_verified=True,
        reserved=True,
        decodable=False,
        family_available=True,
        cross_crop_conflict=False,
    )
    assert status == "REJECTED_RESERVED"
    assert not approved
    assert "RESERVED_MATERIAL" in reasons


def test_image_eligibility_is_separate_from_shortcut_risk():
    status, approved, *_ = approval_for(
        archive_verified=True,
        extraction_verified=True,
        originality="ORIGINAL_VERIFIED",
        crop_identity="CROP_IDENTITY_VERIFIED_FROM_SOURCE",
        licence_verified=True,
        reserved=False,
        decodable=True,
        family_available=True,
        cross_crop_conflict=False,
    )
    assert status == "APPROVED_FOR_CROP_IDENTITY_TRAINING"
    assert approved
    assert dataset_decision(100, "HIGH") == (
        "CONDITIONALLY_APPROVED_PUBLIC_DATASET_BASELINE_ONLY"
    )


def test_missing_integrity_fails_closed():
    status, approved, _, reasons, human_review = approval_for(
        archive_verified=False,
        extraction_verified=False,
        originality="ORIGINAL_VERIFIED",
        crop_identity="CROP_IDENTITY_VERIFIED_FROM_SOURCE",
        licence_verified=True,
        reserved=False,
        decodable=True,
        family_available=True,
        cross_crop_conflict=False,
    )
    assert status == "QUARANTINED_REQUIRES_HUMAN_REVIEW"
    assert not approved
    assert human_review
    assert "ARCHIVE_INTEGRITY_NOT_VERIFIED" in reasons


def test_manifest_hash_is_deterministic():
    rows = [{"b": 2, "a": 1}]
    assert manifest_hash(rows) == manifest_hash(rows)
