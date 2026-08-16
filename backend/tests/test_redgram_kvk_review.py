from __future__ import annotations

from app.modules.disease.models import DiseaseReport
from app.modules.disease.review import export_reviewed_redgram, review_redgram_report


async def _report(db_session, *, consent: bool, status: str):
    from app.modules.auth.models import User
    from app.modules.auth.constants import UserStatus

    user = User(firebase_uid=f"kvk-review-{consent}-{status}", status=UserStatus.ACTIVE)
    db_session.add(user)
    await db_session.flush()
    report = DiseaseReport(
        user_id=user.id,
        image_url="s3://consented/redgram.jpg" if consent else None,
        crop="redgram",
        disease="redgram__healthy",
        confidence=91,
        model_used="redgram_mobilenetv3_small_v1_restricted",
        review_status=status,
        reviewer_role="farmer",
        review_consent=consent,
        kvk_session=True,
        language="en",
    )
    db_session.add(report)
    await db_session.flush()
    return report


async def test_kvk_correction_and_export_only_include_consented(db_session):
    consented = await _report(db_session, consent=True, status="pending")
    declined = await _report(db_session, consent=False, status="declined")
    reviewed = await review_redgram_report(
        db_session,
        report_id=consented.id,
        correct=False,
        corrected_label="redgram__sterility_mosaic",
    )
    assert reviewed.review_status == "corrected"
    assert reviewed.reviewer_role == "kvk_officer"
    exported = await export_reviewed_redgram(db_session)
    assert exported["summary"] == {
        "reviewed_records": 1,
        "confirmed": 0,
        "corrected": 1,
        "class_breakdown": {"redgram__sterility_mosaic": 1},
    }
    assert exported["records"][0]["report_id"] == str(consented.id)
    assert str(declined.id) not in str(exported)
