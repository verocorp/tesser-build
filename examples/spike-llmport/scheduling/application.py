from __future__ import annotations

from typing import Protocol

import tesser.application as ts

import scheduling.client as client
import scheduling.domain as domain


class BookingParts(ts.Parts):

    def __init__(
        self, step: str, name: str, chosen: str, offered: tuple[str, ...]
    ) -> None:
        self.step = step
        self.name = name
        self.chosen = chosen
        self.offered = offered


class SlotDirectory(ts.Port, Protocol):

    def available(self) -> tuple[str, ...]: ...

    def reserve(self, slot: str, name: str) -> None: ...


class BookingRepository(ts.Port, Protocol):

    def has(self, booking_id: str) -> bool: ...

    def get(self, booking_id: str) -> BookingParts: ...

    def save(self, booking_id: str, parts: BookingParts) -> None: ...


class BookingService(ts.ApplicationService):

    def __init__(self, directory: SlotDirectory, repository: BookingRepository) -> None:
        self._directory = directory
        self._repository = repository

    def begin(self, request: client.BeginBookingRequest) -> client.BookingStateResponse:
        if self._repository.has(request.booking_id):
            parts = self._repository.get(request.booking_id)
            booking = domain.Booking(domain.BookingSpec(step=parts.step, name=parts.name, chosen=parts.chosen, offered=parts.offered))
            return client.BookingStateResponse(step=booking.step_label(),
                offered_slots=booking.offered_labels(), reply="continue the booking")
        booking = domain.Booking(domain.BookingSpec(step=domain.COLLECT_NAME, name="", chosen="", offered=()))
        self._repository.save(request.booking_id, BookingParts(step=booking.step_label(),
            name=booking.name_label(), chosen=booking.slot_label(), offered=booking.offered_labels()))
        return client.BookingStateResponse(step=booking.step_label(),
            offered_slots=booking.offered_labels(), reply="ask the caller for their name")

    def provide_name(self, request: client.ProvideNameRequest) -> client.BookingStateResponse:
        parts = self._repository.get(request.booking_id)
        booking = domain.Booking(domain.BookingSpec(step=parts.step, name=parts.name, chosen=parts.chosen, offered=parts.offered))
        booking.provide_name(domain.CustomerName(request.name), tuple(domain.Slot(s) for s in self._directory.available()))
        self._repository.save(request.booking_id, BookingParts(step=booking.step_label(),
            name=booking.name_label(), chosen=booking.slot_label(), offered=booking.offered_labels()))
        return client.BookingStateResponse(step=booking.step_label(),
            offered_slots=booking.offered_labels(), reply="offer the caller the available slots")

    def choose_slot(self, request: client.ChooseSlotRequest) -> client.BookingStateResponse:
        parts = self._repository.get(request.booking_id)
        booking = domain.Booking(domain.BookingSpec(step=parts.step, name=parts.name, chosen=parts.chosen, offered=parts.offered))
        booking.choose_slot(domain.Slot(request.slot))
        self._repository.save(request.booking_id, BookingParts(step=booking.step_label(),
            name=booking.name_label(), chosen=booking.slot_label(), offered=booking.offered_labels()))
        return client.BookingStateResponse(step=booking.step_label(), offered_slots=booking.offered_labels(),
            reply=f"slot {booking.slot_label()} selected; ask the caller to confirm")

    def confirm(self, request: client.ConfirmBookingRequest) -> client.BookingStateResponse:
        parts = self._repository.get(request.booking_id)
        booking = domain.Booking(domain.BookingSpec(step=parts.step, name=parts.name, chosen=parts.chosen, offered=parts.offered))
        booking.confirm()
        self._directory.reserve(booking.slot_label(), booking.name_label())
        self._repository.save(request.booking_id, BookingParts(step=booking.step_label(),
            name=booking.name_label(), chosen=booking.slot_label(), offered=booking.offered_labels()))
        return client.BookingStateResponse(step=booking.step_label(), offered_slots=booking.offered_labels(),
            reply=f"booked {booking.slot_label()} for {booking.name_label()}")

    def reoffer(self, request: client.ReofferRequest) -> client.BookingStateResponse:
        parts = self._repository.get(request.booking_id)
        booking = domain.Booking(domain.BookingSpec(step=parts.step, name=parts.name, chosen=parts.chosen, offered=parts.offered))
        booking.reoffer(tuple(domain.Slot(s) for s in self._directory.available()))
        self._repository.save(request.booking_id, BookingParts(step=booking.step_label(),
            name=booking.name_label(), chosen=booking.slot_label(), offered=booking.offered_labels()))
        return client.BookingStateResponse(step=booking.step_label(),
            offered_slots=booking.offered_labels(), reply="offer the caller the updated slots")

    def status(self, request: client.StatusRequest) -> client.BookingStateResponse:
        parts = self._repository.get(request.booking_id)
        booking = domain.Booking(domain.BookingSpec(step=parts.step, name=parts.name, chosen=parts.chosen, offered=parts.offered))
        return client.BookingStateResponse(step=booking.step_label(),
            offered_slots=booking.offered_labels(), reply="continue the booking")
