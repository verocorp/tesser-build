from __future__ import annotations

import tesser.application as ts

import scheduling.application.parts as parts
import scheduling.client as client
import scheduling.domain as domain


@ts.function
def loaded(stored: parts.BookingParts) -> domain.Booking:
    return domain.Booking(domain.BookingSpec(step=stored.step, name=stored.name, chosen=stored.chosen, offered=stored.offered))


@ts.function
def parts_of(booking: domain.Booking) -> parts.BookingParts:
    return parts.BookingParts(step=booking.step_label(), name=booking.name_label(), chosen=booking.slot_label(), offered=booking.offered_labels())


@ts.function
def state(booking: domain.Booking, reply: str) -> client.BookingStateResponse:
    return client.BookingStateResponse(step=booking.step_label(), offered_slots=booking.offered_labels(), reply=reply)


@ts.function
def reoffered(stored: parts.BookingParts, available: tuple[str, ...]) -> domain.Booking:
    booking = loaded(stored)
    booking.reoffer(tuple(domain.Slot(label) for label in available))
    return booking
