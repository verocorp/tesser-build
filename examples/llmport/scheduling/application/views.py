from __future__ import annotations

import typing

import tesser.application as ts

import scheduling.application.ports.booking_repository as booking_repository
import scheduling.application.ports.slot_directory as slot_directory
import scheduling.client.client as client
import scheduling.domain.scheduling as domain


@ts.function
def _booking(view: booking_repository.BookingView) -> domain.Booking:
    return domain.Booking(
        domain.BookingSpec(step=view.step, name=view.name, chosen=view.chosen, offered=view.offered)
    )


@ts.function
def only(found: booking_repository.FindBookingResponse) -> booking_repository.BookingView:
    match found.presence:
        case booking_repository.BookingPresence.PRESENT:
            return found.bookings[0]
        case booking_repository.BookingPresence.ABSENT:
            raise KeyError("booking not found")
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.function
def loaded(found: booking_repository.FindBookingResponse) -> domain.Booking:
    match found.presence:
        case booking_repository.BookingPresence.PRESENT:
            return _booking(found.bookings[0])
        case booking_repository.BookingPresence.ABSENT:
            raise KeyError("booking not found")
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.function
def began(found: booking_repository.FindBookingResponse) -> domain.Booking:
    match found.presence:
        case booking_repository.BookingPresence.PRESENT:
            return _booking(found.bookings[0])
        case booking_repository.BookingPresence.ABSENT:
            return domain.Booking(
                domain.BookingSpec(step=domain.COLLECT_NAME, name="", chosen="", offered=())
            )
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.function
def begin_reply(found: booking_repository.FindBookingResponse) -> str:
    match found.presence:
        case booking_repository.BookingPresence.PRESENT:
            return "continue the booking"
        case booking_repository.BookingPresence.ABSENT:
            return "ask the caller for their name"
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.function
def save_request(booking_id: str, booking: domain.Booking) -> booking_repository.SaveBookingRequest:
    name = booking.name()
    chosen = booking.chosen()
    return booking_repository.SaveBookingRequest(
        booking_id=booking_id,
        step=str(booking.step()),
        name="" if name is None else str(name),
        chosen="" if chosen is None else str(chosen),
        offered=tuple(str(slot) for slot in booking.offered()),
    )


@ts.function
def state(booking: domain.Booking, reply: str) -> client.BookingStateResponse:
    return client.BookingStateResponse(
        step=str(booking.step()),
        offered_slots=tuple(str(slot) for slot in booking.offered()),
        reply=reply,
    )


@ts.function
def reoffered(view: booking_repository.BookingView, available: tuple[str, ...]) -> domain.Booking:
    booking = _booking(view)
    booking.reoffer(tuple(domain.Slot(label) for label in available))
    return booking


@ts.function
def confirmed(
    reserved: slot_directory.ReserveSlotResponse,
    booking: domain.Booking,
    view: booking_repository.BookingView,
) -> domain.Booking:
    match reserved.outcome:
        case slot_directory.ReservationOutcome.RESERVED:
            return booking
        case slot_directory.ReservationOutcome.SLOT_TAKEN:
            return reoffered(view, reserved.available)
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.function
def confirm_reply(reserved: slot_directory.ReserveSlotResponse, booking: domain.Booking) -> str:
    match reserved.outcome:
        case slot_directory.ReservationOutcome.RESERVED:
            return f"booked {booking.chosen()} for {booking.name()}"
        case slot_directory.ReservationOutcome.SLOT_TAKEN:
            return f"{booking.chosen()} was just taken; offer the caller the updated slots"
        case _ as unreachable:
            typing.assert_never(unreachable)
