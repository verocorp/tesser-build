from __future__ import annotations

import typing

import tesser.application as ts

import scheduling.application.ports.booking_repository as booking_repository
import scheduling.application.ports.slot_directory as slot_directory
import scheduling.client.client as client
import scheduling.domain.scheduling as domain


class MapToBookingSpec(ts.Mapper, domain.BookingSpec):

    def __init__(self, found_booking: booking_repository.FindBookingResponse) -> None:
        match found_booking.presence:
            case booking_repository.BookingPresence.PRESENT:
                view = found_booking.bookings[0]
            case booking_repository.BookingPresence.ABSENT:
                raise KeyError("booking not found")
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            step=view.step, name=view.name, chosen=view.chosen, offered=view.offered
        )


class MapToNamingSpec(ts.Mapper, domain.NamingSpec):

    def __init__(
        self,
        request: client.ProvideNameRequest,
        available: slot_directory.AvailableSlotsResponse,
    ) -> None:
        super().__init__(
            name=request.name, offered=domain.OfferSpec(labels=available.slots)
        )


class MapToSaveBookingRequest(ts.Mapper, booking_repository.SaveBookingRequest):

    def __init__(self, booking: domain.Booking, booking_id: domain.BookingID) -> None:
        stored_name = booking.name()
        stored_chosen = booking.chosen()
        super().__init__(
            booking_id=str(booking_id),
            step=str(booking.step()),
            name="" if stored_name is None else str(stored_name),
            chosen="" if stored_chosen is None else str(stored_chosen),
            offered=tuple(str(slot) for slot in booking.offered()),
        )


class MapToReoffersSpec(ts.Mapper, domain.ReoffersSpec):

    def __init__(self, reserved_slot: slot_directory.ReserveSlotResponse) -> None:
        offered: tuple[tuple[str, ...], ...] = ()
        match reserved_slot.outcome:
            case slot_directory.ReservationOutcome.RESERVED:
                pass
            case slot_directory.ReservationOutcome.SLOT_TAKEN:
                offered = (reserved_slot.available,)
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(offered=offered)


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
