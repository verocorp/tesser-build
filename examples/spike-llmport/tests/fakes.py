from __future__ import annotations

import tesser.testing as ts

from scheduling.application import BookingParts, BookingRepository, SlotDirectory
from scheduling.domain import CustomerName, DomainError, DomainKind, InfraError, Slot


@ts.fake
class MemorySlotDirectory(SlotDirectory):

    def __init__(self, slots: tuple[Slot, ...]) -> None:
        self.slots = list(slots)
        self.reserved: list[tuple[Slot, CustomerName]] = []

    def available(self) -> tuple[Slot, ...]:
        return tuple(self.slots)

    def reserve(self, slot: Slot, name: CustomerName) -> None:
        if slot not in self.slots:
            raise DomainError(
                DomainKind.CONFLICT, "slot_taken", f"slot {slot} was just taken"
            )
        self.slots.remove(slot)
        self.reserved.append((slot, name))


@ts.fake
class MemoryBookingRepository(BookingRepository):

    def __init__(self) -> None:
        self.saved: list[BookingParts] = []

    def save(self, parts: BookingParts) -> None:
        self.saved.append(parts)


@ts.fake
class DownSlotDirectory(SlotDirectory):

    def available(self) -> tuple[Slot, ...]:
        raise InfraError("slot directory unreachable")

    def reserve(self, slot: Slot, name: CustomerName) -> None:
        raise InfraError("slot directory unreachable")
