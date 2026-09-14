from __future__ import annotations

import enum
import typing

import tesser.application as ts


class ReserveSlotOutcome(enum.Enum):
    RESERVED = "reserved"
    SLOT_TAKEN = "slot_taken"


class ListAvailableSlotsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class ListAvailableSlotsResponse(ts.Response):

    def __init__(self, slots: tuple[str, ...]) -> None:
        self.slots = slots


class ReserveSlotRequest(ts.Request):

    def __init__(self, slot: str, name: str) -> None:
        self.slot = slot
        self.name = name


class ReserveSlotResponse(ts.Response):

    def __init__(self, outcome: ReserveSlotOutcome, available: tuple[str, ...]) -> None:
        self.outcome = outcome
        self.available = available


class SlotDirectory(ts.Port, typing.Protocol):

    def list_available_slots(
        self, list_available_slots_request: ListAvailableSlotsRequest
    ) -> ListAvailableSlotsResponse: ...

    def reserve_slot(self, reserve_slot_request: ReserveSlotRequest) -> ReserveSlotResponse: ...
