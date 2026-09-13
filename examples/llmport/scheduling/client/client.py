from __future__ import annotations

import typing

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


class StatusRequest(ts.Request):

    def __init__(self, booking_id: str) -> None:
        self.booking_id = booking_id


class Booking(ts.Response):

    def __init__(self, step: str, offered_slots: tuple[str, ...], reply: str) -> None:
        self.step = step
        self.offered_slots = offered_slots
        self.reply = reply


class BeginResponse(ts.Response):

    def __init__(self, booking: Booking) -> None:
        self.booking = booking


class ProvideNameResponse(ts.Response):

    def __init__(self, booking: Booking) -> None:
        self.booking = booking


class ChooseSlotResponse(ts.Response):

    def __init__(self, booking: Booking) -> None:
        self.booking = booking


class ConfirmResponse(ts.Response):

    def __init__(self, booking: Booking) -> None:
        self.booking = booking


class StatusResponse(ts.Response):

    def __init__(self, booking: Booking) -> None:
        self.booking = booking


class SchedulingClient(ts.Client, typing.Protocol):

    def begin(self, begin_booking_request: BeginBookingRequest) -> BeginResponse: ...

    def provide_name(self, provide_name_request: ProvideNameRequest) -> ProvideNameResponse: ...

    def choose_slot(self, choose_slot_request: ChooseSlotRequest) -> ChooseSlotResponse: ...

    def confirm(self, confirm_booking_request: ConfirmBookingRequest) -> ConfirmResponse: ...

    def status(self, status_request: StatusRequest) -> StatusResponse: ...
