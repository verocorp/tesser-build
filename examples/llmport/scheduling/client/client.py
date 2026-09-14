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


class GetBookingRequest(ts.Request):

    def __init__(self, booking_id: str) -> None:
        self.booking_id = booking_id


class Booking(ts.Response):

    def __init__(self, step: str, offered_slots: tuple[str, ...], reply: str) -> None:
        self.step = step
        self.offered_slots = offered_slots
        self.reply = reply


class BeginBookingResponse(ts.Response):

    def __init__(self, booking: Booking) -> None:
        self.booking = booking


class ProvideNameResponse(ts.Response):

    def __init__(self, booking: Booking) -> None:
        self.booking = booking


class ChooseSlotResponse(ts.Response):

    def __init__(self, booking: Booking) -> None:
        self.booking = booking


class ConfirmBookingResponse(ts.Response):

    def __init__(self, booking: Booking) -> None:
        self.booking = booking


class GetBookingResponse(ts.Response):

    def __init__(self, booking: Booking) -> None:
        self.booking = booking


class SchedulingClient(ts.Client, typing.Protocol):

    def begin_booking(self, begin_booking_request: BeginBookingRequest) -> BeginBookingResponse: ...

    def provide_name(self, provide_name_request: ProvideNameRequest) -> ProvideNameResponse: ...

    def choose_slot(self, choose_slot_request: ChooseSlotRequest) -> ChooseSlotResponse: ...

    def confirm_booking(
        self, confirm_booking_request: ConfirmBookingRequest
    ) -> ConfirmBookingResponse: ...

    def get_booking(self, get_booking_request: GetBookingRequest) -> GetBookingResponse: ...
