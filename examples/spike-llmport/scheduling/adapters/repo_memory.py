from __future__ import annotations

import tesser.adapters as ts

import scheduling.application.parts as parts


class MemoryBookingRepository(ts.Repository):
    """The in-memory booking store — a real adapter, not a test double.

    Promoted from a @ts.fake declared byte-identically in two test modules;
    see directory_memory.py for the reasoning.
    """

    def __init__(self) -> None:
        self.stored: dict[str, parts.BookingParts] = {}

    def has(self, booking_id: str) -> bool:
        return booking_id in self.stored

    def get(self, booking_id: str) -> parts.BookingParts:
        return self.stored[booking_id]

    def save(self, booking_id: str, booking: parts.BookingParts) -> None:
        self.stored[booking_id] = booking
