from __future__ import annotations

import enum
import typing

import tesser.application as ts


class ReservationOutcome(enum.Enum):
    RESERVED = "reserved"
    SLOT_TAKEN = "slot_taken"


class AvailableSlotsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class AvailableSlotsResponse(ts.Response):

    def __init__(self, slots: tuple[str, ...]) -> None:
        self.slots = slots


class ReserveSlotRequest(ts.Request):

    def __init__(self, slot: str, name: str) -> None:
        self.slot = slot
        self.name = name


class ReserveSlotResponse(ts.Response):

    def __init__(self, outcome: ReservationOutcome, available: tuple[str, ...]) -> None:
        self.outcome = outcome
        self.available = available


class SlotDirectory(ts.Port, typing.Protocol):

    def available(self, request: AvailableSlotsRequest) -> AvailableSlotsResponse: ...

    def reserve(self, request: ReserveSlotRequest) -> ReserveSlotResponse: ...
