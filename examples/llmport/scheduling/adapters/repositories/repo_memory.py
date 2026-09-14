from __future__ import annotations

import tesser.adapters as ts

import scheduling.application.ports as ports


class MemoryBookingRepository(ts.Repository):
    def __init__(self) -> None:
        self.stored: dict[str, ports.Booking] = {}

    def find_booking(
        self, find_booking_request: ports.FindBookingRequest
    ) -> ports.FindBookingResponse:
        row = self.stored.get(find_booking_request.booking_id)
        if row is None:
            return ports.FindBookingResponse(
                outcome=ports.FindBookingOutcome.ABSENT, bookings=()
            )
        return ports.FindBookingResponse(
            outcome=ports.FindBookingOutcome.PRESENT, bookings=(row,)
        )

    def save_booking(
        self, save_booking_request: ports.SaveBookingRequest
    ) -> ports.SaveBookingResponse:
        self.stored[save_booking_request.booking_id] = ports.Booking(
            step=save_booking_request.step,
            name=save_booking_request.name,
            chosen=save_booking_request.chosen,
            offered=save_booking_request.offered,
        )
        return ports.SaveBookingResponse()
