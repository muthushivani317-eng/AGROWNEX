import json
from types import SimpleNamespace

from app.field_testing.logger import FieldTestLogger


def test_field_test_logger_writes_exportable_privacy_minimized_jsonl(tmp_path) -> None:
    path = tmp_path / "controlled_predictions.jsonl"
    logger = FieldTestLogger(path)
    tester = SimpleNamespace(user=SimpleNamespace(id="private-user-id"), role="kvk_reviewer")

    logger.record(
        tester=tester,
        crop="banana",
        model_id="banana-v3.0.0",
        predicted_class="banana__healthy",
        confidence=0.91,
        outcome="accepted",
    )

    row = json.loads(path.read_text("utf-8"))
    assert row["record_type"] == "KVK_CONTROLLED_FIELD_TEST_PREDICTION"
    assert row["crop"] == "banana"
    assert row["predicted_class"] == "banana__healthy"
    assert row["confidence"] == 0.91
    assert row["timestamp_utc"].endswith("+00:00")
    assert row["tester_role"] == "kvk_reviewer"
    assert row["tester_subject_hash"] != "private-user-id"
    assert "private-user-id" not in path.read_text("utf-8")
