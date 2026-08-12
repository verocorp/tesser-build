from __future__ import annotations

import tesser.application as ts

import scheduling.application.parts as parts
import scheduling.client.client as client
import scheduling.domain.scheduling as domain


@ts.function
def loaded(stored: parts.BookingParts) -> domain.Booking:
    return domain.Booking(domain.BookingSpec(step=stored.step, name=stored.name, chosen=stored.chosen, offered=stored.offered))


@ts.function
def parts_of(booking: domain.Booking) -> parts.BookingParts:
    name = booking.name()
    chosen = booking.chosen()
    return parts.BookingParts(
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
def reoffered(stored: parts.BookingParts, available: tuple[str, ...]) -> domain.Booking:
    booking = loaded(stored)
    booking.reoffer(tuple(domain.Slot(label) for label in available))
    return booking
