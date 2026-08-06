from __future__ import annotations

from typing import Protocol

import tesser.context as ts


class BeginBookingRequest(ts.Request):

    def __init__(self, booking_id: str) -> None:
        self.booking_id = booking_id


class ProvideNameRequest(ts.Request):

    def __init__(self, booking_id: str, name: str) -> None:
        self.booking_id = booking_id
        self.name = name


class ChooseSlotRequest(ts.Request):

    def __init__(self, booking_id: str, slot: str) -> None:
        self.booking_id = booking_id
        self.slot = slot


class ConfirmBookingRequest(ts.Request):

    def __init__(self, booking_id: str) -> None:
        self.booking_id = booking_id


class ReofferRequest(ts.Request):

    def __init__(self, booking_id: str) -> None:
        self.booking_id = booking_id


class StatusRequest(ts.Request):

    def __init__(self, booking_id: str) -> None:
        self.booking_id = booking_id


class BookingStateResponse(ts.Response):

    def __init__(self, step: str, offered_slots: tuple[str, ...], reply: str) -> None:
        self.step = step
        self.offered_slots = offered_slots
        self.reply = reply


class SchedulingClient(ts.Client, Protocol):

    def begin(self, request: BeginBookingRequest) -> BookingStateResponse: ...

    def provide_name(self, request: ProvideNameRequest) -> BookingStateResponse: ...

    def choose_slot(self, request: ChooseSlotRequest) -> BookingStateResponse: ...

    def confirm(self, request: ConfirmBookingRequest) -> BookingStateResponse: ...

    def reoffer(self, request: ReofferRequest) -> BookingStateResponse: ...

    def status(self, request: StatusRequest) -> BookingStateResponse: ...
