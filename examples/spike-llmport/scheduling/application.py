from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, assert_never

import tesser.application as ts

from scheduling.domain import (
    Booking,
    BookingSpec,
    ChooseSlot,
    ConfirmBooking,
    CustomerName,
    DomainError,
    DomainKind,
    ProvideName,
    Slot,
)
from scheduling.tools import ToolName, allowed_tools, parse, schema_for


class BookingParts(ts.Parts):

    def __init__(self, name: str, slot: str) -> None:
        self.name = name
        self.slot = slot


class SlotDirectory(ts.Port, Protocol):

    def available(self) -> tuple[Slot, ...]: ...

    def reserve(self, slot: Slot, name: CustomerName) -> None: ...


class BookingRepository(ts.Port, Protocol):

    def save(self, parts: BookingParts) -> None: ...


class BookingService(ts.ApplicationService):

    def __init__(self, directory: SlotDirectory, repository: BookingRepository) -> None:
        self._directory = directory
        self._repository = repository

    def begin(self) -> Booking:
        return Booking(BookingSpec())

    def llm_tools(self, booking: Booking) -> dict[ToolName, dict[str, object]]:
        return {
            name: schema_for(name, booking) for name in allowed_tools(booking.step())
        }

    def execute(
        self, booking: Booking, name: ToolName, raw_arguments: Mapping[str, object]
    ) -> str:
        command = parse(name, raw_arguments)
        match command:
            case ProvideName():
                booking.provide_name(command.name(), self._directory.available())
                offered = ", ".join(str(s) for s in booking.offered_slots())
                return f"name recorded; available slots: {offered}"
            case ChooseSlot():
                booking.choose_slot(command.slot())
                return f"slot {booking.chosen_slot()} selected; awaiting confirmation"
            case ConfirmBooking():
                self._reserve(booking)
                booking.confirm()
                self._repository.save(
                    BookingParts(
                        name=str(booking.customer_name()),
                        slot=str(booking.chosen_slot()),
                    )
                )
                return f"booked {booking.chosen_slot()} for {booking.customer_name()}"
        assert_never(command)

    def _reserve(self, booking: Booking) -> None:
        try:
            self._directory.reserve(booking.chosen_slot(), booking.customer_name())
        except DomainError as err:
            if err.kind is not DomainKind.CONFLICT:
                raise
            booking.reoffer(self._directory.available())
            offered = ", ".join(str(s) for s in booking.offered_slots())
            raise DomainError(
                DomainKind.CONFLICT,
                err.code,
                f"{err.message}; now available: {offered}",
            ) from err
