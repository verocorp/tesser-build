from __future__ import annotations

import tesser.adapters as ts

import scheduling.application.ports as ports


class MemorySlotDirectory(ts.Gateway):
    def __init__(self, slots: tuple[str, ...]) -> None:
        self.slots = list(slots)
        self.reserved: list[tuple[str, str]] = []

    def list_available_slots(
        self, list_available_slots_request: ports.ListAvailableSlotsRequest
    ) -> ports.ListAvailableSlotsResponse:
        return ports.ListAvailableSlotsResponse(slots=tuple(self.slots))

    def reserve_slot(
        self, reserve_slot_request: ports.ReserveSlotRequest
    ) -> ports.ReserveSlotResponse:
        if reserve_slot_request.slot not in self.slots:
            return ports.ReserveSlotResponse(
                outcome=ports.ReserveSlotOutcome.SLOT_TAKEN, available=tuple(self.slots)
            )
        self.slots.remove(reserve_slot_request.slot)
        self.reserved.append((reserve_slot_request.slot, reserve_slot_request.name))
        return ports.ReserveSlotResponse(
            outcome=ports.ReserveSlotOutcome.RESERVED, available=()
        )
