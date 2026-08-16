import json

from app.banana_v3.prediction_logger import JsonlLogger


def test_jsonl_logger_is_append_only_and_privacy_allowlisted_by_caller(tmp_path):
    path = tmp_path / "log.jsonl"
    logger = JsonlLogger(path)
    logger.append({"request_id": "one", "runtime": "onnx"})
    logger.append({"request_id": "two", "runtime": "pytorch"})
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [row["request_id"] for row in rows] == ["one", "two"]
