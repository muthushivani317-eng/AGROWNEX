import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACKETS = ROOT / "recommendation_knowledge/review_packets"


def test_all_packets_remain_pending_human_review():
    packets = list(PACKETS.glob("*/*/packet.json"))
    assert packets
    for path in packets:
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["mapping_status"] == "PENDING_HUMAN_REVIEW"
        assert document["human_approval_status"] == "PENDING"


def test_unknown_authority_candidates_are_not_final_authority_eligible():
    for path in PACKETS.glob("*/*/candidates.json"):
        for item in json.loads(path.read_text(encoding="utf-8")):
            if item["source_authority"] == "UNKNOWN_AUTHORITY":
                assert item["final_authority_eligible"] is False


def test_tamil_drafts_are_not_approved():
    for path in PACKETS.glob("*/*/tamil_draft.json"):
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["status"] != "HUMAN_APPROVED"
        assert document["approval_status"] == "PENDING"
