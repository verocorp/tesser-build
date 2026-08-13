from __future__ import annotations

import tesser.adapters as ts

import scheduling.application.ports.booking_repository as booking_repository


class MemoryBookingRepository(ts.Repository):
    def __init__(self) -> None:
        self.stored: dict[str, booking_repository.BookingView] = {}

    def find(self, request: booking_repository.FindBookingRequest) -> booking_repository.FindBookingResponse:
        row = self.stored.get(request.booking_id)
        if row is None:
            return booking_repository.FindBookingResponse(
                presence=booking_repository.BookingPresence.ABSENT, bookings=()
            )
        return booking_repository.FindBookingResponse(
            presence=booking_repository.BookingPresence.PRESENT, bookings=(row,)
        )

    def save(self, request: booking_repository.SaveBookingRequest) -> booking_repository.SaveBookingResponse:
        self.stored[request.booking_id] = booking_repository.BookingView(
            step=request.step, name=request.name, chosen=request.chosen, offered=request.offered
        )
        return booking_repository.SaveBookingResponse()
