from __future__ import annotations

import enum
import typing

import tesser.application as ts


class FindBookingOutcome(enum.Enum):
    PRESENT = "present"
    ABSENT = "absent"


class Booking(ts.Response):

    def __init__(self, step: str, name: str, chosen: str, offered: tuple[str, ...]) -> None:
        self.step = step
        self.name = name
        self.chosen = chosen
        self.offered = offered


class FindBookingRequest(ts.Request):

    def __init__(self, booking_id: str) -> None:
        self.booking_id = booking_id


class FindBookingResponse(ts.Response):

    def __init__(self, outcome: FindBookingOutcome, bookings: tuple[Booking, ...]) -> None:
        self.outcome = outcome
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


class BookingRepository(ts.Port, typing.Protocol):

    def find_booking(self, find_booking_request: FindBookingRequest) -> FindBookingResponse: ...

    def save_booking(self, save_booking_request: SaveBookingRequest) -> SaveBookingResponse: ...
