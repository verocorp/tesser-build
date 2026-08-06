from __future__ import annotations

import tesser.testing as ts

from scheduling.application import BookingParts, BookingRepository, SlotDirectory


@ts.fake
class MemorySlotDirectory(SlotDirectory):

    def __init__(self, slots: tuple[str, ...]) -> None:
        self.slots = list(slots)
        self.reserved: list[tuple[str, str]] = []

    def available(self) -> tuple[str, ...]:
        return tuple(self.slots)

    def reserve(self, slot: str, name: str) -> None:
        if slot not in self.slots:
            raise ValueError(f"slot {slot} was just taken")
        self.slots.remove(slot)
        self.reserved.append((slot, name))


@ts.fake
class MemoryBookingRepository(BookingRepository):

    def __init__(self) -> None:
        self.stored: dict[str, BookingParts] = {}

    def get(self, booking_id: str) -> BookingParts:
        return self.stored[booking_id]

    def save(self, booking_id: str, parts: BookingParts) -> None:
        self.stored[booking_id] = parts


@ts.fake
class DownSlotDirectory(SlotDirectory):

    def available(self) -> tuple[str, ...]:
        raise RuntimeError("slot directory unreachable")

    def reserve(self, slot: str, name: str) -> None:
        raise RuntimeError("slot directory unreachable")
