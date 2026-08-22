from __future__ import annotations

import typing

import tesser.application as ts

import scheduling.application.ports.booking_repository as booking_repository
import scheduling.application.ports.slot_directory as slot_directory
import scheduling.domain.scheduling as domain


class MapToBookingSpec(ts.Mapper):

    def __init__(self, found_booking: booking_repository.FindBookingResponse) -> None:
        match found_booking.presence:
            case booking_repository.BookingPresence.PRESENT:
                view = found_booking.bookings[0]
            case booking_repository.BookingPresence.ABSENT:
                raise KeyError("booking not found")
            case _ as unreachable:
                typing.assert_never(unreachable)
        self._step = view.step
        self._name = view.name
        self._chosen = view.chosen
        self._offered = view.offered

    @property
    def step(self) -> str:
        return self._step

    @property
    def name(self) -> str:
        return self._name

    @property
    def chosen(self) -> str:
        return self._chosen

    @property
    def offered(self) -> tuple[str, ...]:
        return self._offered


class MapToReofferedSlots(ts.Mapper):

    def __init__(self, reserved_slot: slot_directory.ReserveSlotResponse) -> None:
        self._slots = reserved_slot.available

    @property
    def slots(self) -> tuple[str, ...]:
        return self._slots


class MapToSettledBooking(ts.Mapper):

    def __init__(self, reserved_slot: slot_directory.ReserveSlotResponse) -> None:
        self._reoffered_slots_mappers: tuple[MapToReofferedSlots, ...] = ()
        match reserved_slot.outcome:
            case slot_directory.ReservationOutcome.RESERVED:
                pass
            case slot_directory.ReservationOutcome.SLOT_TAKEN:
                self._reoffered_slots_mappers = (
                    MapToReofferedSlots(reserved_slot=reserved_slot),
                )
            case _ as unreachable:
                typing.assert_never(unreachable)

    @property
    def reoffered_slots_mappers(self) -> tuple[MapToReofferedSlots, ...]:
        return self._reoffered_slots_mappers


def began(found: booking_repository.FindBookingResponse) -> domain.Booking:  # tesser:debt TB051
    match found.presence:
        case booking_repository.BookingPresence.PRESENT:
            view = found.bookings[0]
            return domain.Booking(
                domain.BookingSpec(
                    step=view.step, name=view.name, chosen=view.chosen, offered=view.offered
                )
            )
        case booking_repository.BookingPresence.ABSENT:
            return domain.Booking(
                domain.BookingSpec(step=domain.COLLECT_NAME, name="", chosen="", offered=())
            )
        case _ as unreachable:
            typing.assert_never(unreachable)


def begin_reply(found: booking_repository.FindBookingResponse) -> str:  # tesser:debt TB051
    match found.presence:
        case booking_repository.BookingPresence.PRESENT:
            return "continue the booking"
        case booking_repository.BookingPresence.ABSENT:
            return "ask the caller for their name"
        case _ as unreachable:
            typing.assert_never(unreachable)


def confirm_reply(reserved: slot_directory.ReserveSlotResponse, booking: domain.Booking) -> str:  # tesser:debt TB051
    match reserved.outcome:
        case slot_directory.ReservationOutcome.RESERVED:
            return f"booked {booking.chosen()} for {booking.name()}"
        case slot_directory.ReservationOutcome.SLOT_TAKEN:
            return f"{booking.chosen()} was just taken; offer the caller the updated slots"
        case _ as unreachable:
            typing.assert_never(unreachable)
