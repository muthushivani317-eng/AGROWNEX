import uuid
from datetime import datetime, timezone

from app.banana_v3.schemas import DiseaseBlock, GateBlock, PredictionResponse, ResultBlock


def test_response_schema_matches_contract():
    response = PredictionResponse(
        request_id=uuid.uuid4(),
        status="uncertain",
        decision_code="BV3_HG_UNCERTAIN",
        result=ResultBlock(confidence=0.5, margin=0.1),
        healthy_gate=GateBlock(predicted_class="banana__diseased", confidence=0.5, margin=0.1, accepted=False),
        disease_classifier=DiseaseBlock(executed=False, confidence=0, margin=0, accepted=False),
        message_key="banana.result.unable_to_confirm",
        requires_follow_up_photo=True,
        requires_human_review=True,
        runtime_backend="pytorch",
        processing_time_ms=1,
        timestamp_utc=datetime.now(timezone.utc),
    )
    assert response.result.class_id is None
