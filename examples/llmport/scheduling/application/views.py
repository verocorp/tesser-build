from __future__ import annotations

import typing

import tesser.application as ts

import scheduling.application.ports.booking_repository as booking_repository
import scheduling.application.ports.slot_directory as slot_directory
import scheduling.domain.scheduling as domain


@ts.do_not_use_function
def only(found: booking_repository.FindBookingResponse) -> booking_repository.BookingView:  # tesser:debt TB051
    match found.presence:
        case booking_repository.BookingPresence.PRESENT:
            return found.bookings[0]
        case booking_repository.BookingPresence.ABSENT:
            raise KeyError("booking not found")
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def loaded(found: booking_repository.FindBookingResponse) -> domain.Booking:  # tesser:debt TB051
    match found.presence:
        case booking_repository.BookingPresence.PRESENT:
            view = found.bookings[0]
            return domain.Booking(
                domain.BookingSpec(
                    step=view.step, name=view.name, chosen=view.chosen, offered=view.offered
                )
            )
        case booking_repository.BookingPresence.ABSENT:
            raise KeyError("booking not found")
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
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


@ts.do_not_use_function
def begin_reply(found: booking_repository.FindBookingResponse) -> str:  # tesser:debt TB051
    match found.presence:
        case booking_repository.BookingPresence.PRESENT:
            return "continue the booking"
        case booking_repository.BookingPresence.ABSENT:
            return "ask the caller for their name"
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def confirmed(  # tesser:debt TB051
    reserved: slot_directory.ReserveSlotResponse,
    booking: domain.Booking,
    view: booking_repository.BookingView,
) -> domain.Booking:
    match reserved.outcome:
        case slot_directory.ReservationOutcome.RESERVED:
            return booking
        case slot_directory.ReservationOutcome.SLOT_TAKEN:
            stored = domain.Booking(
                domain.BookingSpec(
                    step=view.step, name=view.name, chosen=view.chosen, offered=view.offered
                )
            )
            stored.reoffer(tuple(domain.Slot(label) for label in reserved.available))
            return stored
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.do_not_use_function
def confirm_reply(reserved: slot_directory.ReserveSlotResponse, booking: domain.Booking) -> str:  # tesser:debt TB051
    match reserved.outcome:
        case slot_directory.ReservationOutcome.RESERVED:
            return f"booked {booking.chosen()} for {booking.name()}"
        case slot_directory.ReservationOutcome.SLOT_TAKEN:
            return f"{booking.chosen()} was just taken; offer the caller the updated slots"
        case _ as unreachable:
            typing.assert_never(unreachable)
