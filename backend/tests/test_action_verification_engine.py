import base64

import pytest
from app.modules.action_verification.engine import (
    ActionStatus,
    OutcomeStatus,
    WorkflowTransitionError,
    transition,
)
from app.modules.action_verification.evidence import EvidenceValidationError, validate_evidence
from app.modules.action_verification.schemas import ActionRespondIn


def test_suggested_can_be_reported_done_without_photo() -> None:
    result = transition(ActionStatus.SUGGESTED, "done")
    assert result == ActionStatus.FARMER_REPORTED_DONE


def test_done_is_never_agronomic_success() -> None:
    result = transition(ActionStatus.SUGGESTED, "done")
    assert result.value == "farmer_reported_done"
    assert "success" not in result.value


def test_done_not_done_deferred_and_correction_transitions() -> None:
    assert transition(ActionStatus.SUGGESTED, "not_done") == ActionStatus.FARMER_REPORTED_NOT_DONE
    assert transition(ActionStatus.VIEWED, "defer") == ActionStatus.DEFERRED
    assert transition(ActionStatus.FARMER_REPORTED_DONE, "correct") == ActionStatus.CORRECTED


def test_invalid_transition_rejected() -> None:
    with pytest.raises(WorkflowTransitionError):
        transition(ActionStatus.CANCELLED, "done")


def test_outcome_vocabulary_contains_no_inferred_success() -> None:
    assert "agronomic_success" not in {item.value for item in OutcomeStatus}


def test_photo_requires_explicit_consent_and_valid_image() -> None:
    encoded = base64.b64encode(b"not-image").decode()
    with pytest.raises(EvidenceValidationError, match="CONSENT"):
        validate_evidence(encoded, "image/jpeg", consent=False)
    with pytest.raises(EvidenceValidationError, match="CORRUPT"):
        validate_evidence(encoded, "image/jpeg", consent=True)


def test_release_contract_explicitly_defers_optional_evidence_upload() -> None:
    encoded = base64.b64encode(b"not-image").decode()
    with pytest.raises(ValueError, match="EVIDENCE_UPLOAD_NOT_AVAILABLE"):
        ActionRespondIn(
            event="done", expected_version=1, idempotency_key="evidence-key-1",
            request_id="evidence-request", evidence_base64=encoded,
            evidence_mime_type="image/jpeg", retention_consent=True,
        )
