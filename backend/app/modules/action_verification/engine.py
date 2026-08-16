from enum import StrEnum


class ActionStatus(StrEnum):
    SUGGESTED = "suggested"
    VIEWED = "viewed"
    FARMER_REPORTED_DONE = "farmer_reported_done"
    FARMER_REPORTED_NOT_DONE = "farmer_reported_not_done"
    DEFERRED = "deferred"
    CORRECTED = "corrected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SKIPPED = "skipped"
    UNABLE_TO_COMPLETE = "unable_to_complete"


class OutcomeStatus(StrEnum):
    NOT_REPORTED = "not_reported"
    FARMER_REPORTS_IMPROVED = "farmer_reports_improved"
    FARMER_REPORTS_NO_CHANGE = "farmer_reports_no_change"
    FARMER_REPORTS_WORSE = "farmer_reports_worse"
    EXPERT_REVIEW_PENDING = "expert_review_pending"
    EXPERT_REVIEWED = "expert_reviewed"


class WorkflowTransitionError(ValueError):
    pass


def transition(current: ActionStatus, event: str) -> ActionStatus:
    if current == ActionStatus.CANCELLED:
        raise WorkflowTransitionError("ACTION_CANCELLED")
    mapping = {
        "view": ActionStatus.VIEWED,
        "done": ActionStatus.FARMER_REPORTED_DONE,
        "not_done": ActionStatus.FARMER_REPORTED_NOT_DONE,
        "defer": ActionStatus.DEFERRED,
        "correct": ActionStatus.CORRECTED,
        "cancel": ActionStatus.CANCELLED,
        "skip": ActionStatus.SKIPPED,
        "unable": ActionStatus.UNABLE_TO_COMPLETE,
    }
    if event not in mapping:
        raise WorkflowTransitionError("INVALID_ACTION_EVENT")
    if event == "correct" and current not in {
        ActionStatus.FARMER_REPORTED_DONE,
        ActionStatus.FARMER_REPORTED_NOT_DONE,
        ActionStatus.DEFERRED,
    }:
        raise WorkflowTransitionError("NOTHING_TO_CORRECT")
    return mapping[event]
