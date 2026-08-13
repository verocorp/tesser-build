from __future__ import annotations

import enum
from typing import Protocol

import tesser.application as ts


class BookingPresence(enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"


class BookingView(ts.Response):

    def __init__(self, step: str, name: str, chosen: str, offered: tuple[str, ...]) -> None:
        self.step = step
        self.name = name
        self.chosen = chosen
        self.offered = offered


class FindBookingRequest(ts.Request):

    def __init__(self, booking_id: str) -> None:
        self.booking_id = booking_id


class FindBookingResponse(ts.Response):

    def __init__(self, presence: BookingPresence, bookings: tuple[BookingView, ...]) -> None:
        self.presence = presence
        self.bookings = bookings


class SaveBookingRequest(ts.Request):

    def __init__(
        self, booking_id: str, step: str, name: str, chosen: str, offered: tuple[str, ...]
    ) -> None:
        self.booking_id = booking_id
        self.step = step
        self.name = name
        self.chosen = chosen
        self.offered = offered


class SaveBookingResponse(ts.Response):

    def __init__(self) -> None:
        return None


class BookingRepository(ts.Port, Protocol):

    def find(self, request: FindBookingRequest) -> FindBookingResponse: ...

    def save(self, request: SaveBookingRequest) -> SaveBookingResponse: ...
