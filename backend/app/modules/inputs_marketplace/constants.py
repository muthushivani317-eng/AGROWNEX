from enum import StrEnum


class InputCategory(StrEnum):
    SEED = "seed"
    FERTILIZER = "fertilizer"
    PESTICIDE = "pesticide"


class InputOrderStatus(StrEnum):
    PLACED = "placed"
    CONFIRMED = "confirmed"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"


STATUS_TRANSITIONS = {
    InputOrderStatus.PLACED: {InputOrderStatus.CONFIRMED},
    InputOrderStatus.CONFIRMED: {InputOrderStatus.OUT_FOR_DELIVERY},
    InputOrderStatus.OUT_FOR_DELIVERY: {InputOrderStatus.DELIVERED},
    InputOrderStatus.DELIVERED: set(),
}
