from __future__ import annotations

import tesser.adapters as ts

import scheduling.application.ports.slot_directory as slot_directory


class MemorySlotDirectory(ts.Gateway):
    def __init__(self, slots: tuple[str, ...]) -> None:
        self.slots = list(slots)
        self.reserved: list[tuple[str, str]] = []

    def available(self, request: slot_directory.AvailableSlotsRequest) -> slot_directory.AvailableSlotsResponse:
        return slot_directory.AvailableSlotsResponse(slots=tuple(self.slots))

    def reserve(self, request: slot_directory.ReserveSlotRequest) -> slot_directory.ReserveSlotResponse:
        if request.slot not in self.slots:
            return slot_directory.ReserveSlotResponse(
                outcome=slot_directory.ReservationOutcome.SLOT_TAKEN, available=tuple(self.slots)
            )
        self.slots.remove(request.slot)
        self.reserved.append((request.slot, request.name))
        return slot_directory.ReserveSlotResponse(
            outcome=slot_directory.ReservationOutcome.RESERVED, available=()
        )
