from __future__ import annotations

from typing import Protocol

import tesser.application as ts

from scheduling.client import (
    BeginBookingRequest,
    BookingStateResponse,
    ChooseSlotRequest,
    ConfirmBookingRequest,
    ProvideNameRequest,
    ReofferRequest,
    StatusRequest,
)
from scheduling.domain import COLLECT_NAME, Booking, BookingSpec, CustomerName, Slot


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

    def get(self, booking_id: str) -> BookingParts: ...

    def save(self, booking_id: str, parts: BookingParts) -> None: ...


class BookingService(ts.ApplicationService):

    def __init__(self, directory: SlotDirectory, repository: BookingRepository) -> None:
        self._directory = directory
        self._repository = repository

    def begin(self, request: BeginBookingRequest) -> BookingStateResponse:
        booking = Booking(BookingSpec(step=COLLECT_NAME, name="", chosen="", offered=()))
        self._repository.save(request.booking_id, BookingParts(step=booking.step_label(),
            name=booking.name_label(), chosen=booking.slot_label(), offered=booking.offered_labels()))
        return BookingStateResponse(step=booking.step_label(),
            offered_slots=booking.offered_labels(), reply="ask the caller for their name")

    def provide_name(self, request: ProvideNameRequest) -> BookingStateResponse:
        parts = self._repository.get(request.booking_id)
        booking = Booking(BookingSpec(step=parts.step, name=parts.name, chosen=parts.chosen, offered=parts.offered))
        booking.provide_name(CustomerName(request.name), tuple(Slot(s) for s in self._directory.available()))
        self._repository.save(request.booking_id, BookingParts(step=booking.step_label(),
            name=booking.name_label(), chosen=booking.slot_label(), offered=booking.offered_labels()))
        return BookingStateResponse(step=booking.step_label(),
            offered_slots=booking.offered_labels(), reply="offer the caller the available slots")

    def choose_slot(self, request: ChooseSlotRequest) -> BookingStateResponse:
        parts = self._repository.get(request.booking_id)
        booking = Booking(BookingSpec(step=parts.step, name=parts.name, chosen=parts.chosen, offered=parts.offered))
        booking.choose_slot(Slot(request.slot))
        self._repository.save(request.booking_id, BookingParts(step=booking.step_label(),
            name=booking.name_label(), chosen=booking.slot_label(), offered=booking.offered_labels()))
        return BookingStateResponse(step=booking.step_label(), offered_slots=booking.offered_labels(),
            reply=f"slot {booking.slot_label()} selected; ask the caller to confirm")

    def confirm(self, request: ConfirmBookingRequest) -> BookingStateResponse:
        parts = self._repository.get(request.booking_id)
        booking = Booking(BookingSpec(step=parts.step, name=parts.name, chosen=parts.chosen, offered=parts.offered))
        booking.confirm()
        self._directory.reserve(booking.slot_label(), booking.name_label())
        self._repository.save(request.booking_id, BookingParts(step=booking.step_label(),
            name=booking.name_label(), chosen=booking.slot_label(), offered=booking.offered_labels()))
        return BookingStateResponse(step=booking.step_label(), offered_slots=booking.offered_labels(),
            reply=f"booked {booking.slot_label()} for {booking.name_label()}")

    def reoffer(self, request: ReofferRequest) -> BookingStateResponse:
        parts = self._repository.get(request.booking_id)
        booking = Booking(BookingSpec(step=parts.step, name=parts.name, chosen=parts.chosen, offered=parts.offered))
        booking.reoffer(tuple(Slot(s) for s in self._directory.available()))
        self._repository.save(request.booking_id, BookingParts(step=booking.step_label(),
            name=booking.name_label(), chosen=booking.slot_label(), offered=booking.offered_labels()))
        return BookingStateResponse(step=booking.step_label(),
            offered_slots=booking.offered_labels(), reply="offer the caller the updated slots")

    def status(self, request: StatusRequest) -> BookingStateResponse:
        parts = self._repository.get(request.booking_id)
        booking = Booking(BookingSpec(step=parts.step, name=parts.name, chosen=parts.chosen, offered=parts.offered))
        return BookingStateResponse(step=booking.step_label(),
            offered_slots=booking.offered_labels(), reply="continue the booking")
