from __future__ import annotations

from typing import Protocol

import tesser.application as ts

import scheduling.application.parts as parts
import scheduling.application.views as views
import scheduling.client.client as client
import scheduling.domain.scheduling as domain


class SlotDirectory(ts.Port, Protocol):

    def available(self) -> tuple[str, ...]: ...

    def reserve(self, slot: str, name: str) -> parts.Reserved | parts.SlotTaken: ...


class BookingRepository(ts.Port, Protocol):

    def has(self, booking_id: str) -> bool: ...

    def get(self, booking_id: str) -> parts.BookingParts: ...

    def save(self, booking_id: str, stored: parts.BookingParts) -> None: ...


class BookingService(ts.ApplicationService):

    def __init__(self, directory: SlotDirectory, repository: BookingRepository) -> None:
        self._directory = directory
        self._repository = repository

    def begin(self, request: client.BeginBookingRequest) -> client.BookingStateResponse:
        if self._repository.has(request.booking_id):
            return views.state(views.loaded(self._repository.get(request.booking_id)), "continue the booking")
        booking = domain.Booking(domain.BookingSpec(step=domain.COLLECT_NAME, name="", chosen="", offered=()))
        self._repository.save(request.booking_id, views.parts_of(booking))
        return views.state(booking, "ask the caller for their name")

    def provide_name(self, request: client.ProvideNameRequest) -> client.BookingStateResponse:
        booking = views.loaded(self._repository.get(request.booking_id))
        booking.provide_name(domain.CustomerName(request.name), tuple(domain.Slot(label) for label in self._directory.available()))
        self._repository.save(request.booking_id, views.parts_of(booking))
        return views.state(booking, "offer the caller the available slots")

    def choose_slot(self, request: client.ChooseSlotRequest) -> client.BookingStateResponse:
        booking = views.loaded(self._repository.get(request.booking_id))
        booking.choose_slot(domain.Slot(request.slot))
        self._repository.save(request.booking_id, views.parts_of(booking))
        return views.state(booking, f"slot {booking.slot_label()} selected; ask the caller to confirm")

    def confirm(self, request: client.ConfirmBookingRequest) -> client.BookingStateResponse:
        stored = self._repository.get(request.booking_id)
        booking = views.loaded(stored)
        booking.confirm()
        match self._directory.reserve(booking.slot_label(), booking.name_label()):
            case parts.Reserved():
                settled, reply = booking, f"booked {booking.slot_label()} for {booking.name_label()}"
            case parts.SlotTaken(available=fresh):
                settled, reply = views.reoffered(stored, fresh), f"{booking.slot_label()} was just taken; offer the caller the updated slots"
        self._repository.save(request.booking_id, views.parts_of(settled))
        return views.state(settled, reply)

    def status(self, request: client.StatusRequest) -> client.BookingStateResponse:
        return views.state(views.loaded(self._repository.get(request.booking_id)), "continue the booking")
