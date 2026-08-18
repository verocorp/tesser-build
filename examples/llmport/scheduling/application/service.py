from __future__ import annotations

import tesser.application as ts

import scheduling.application.ports.booking_repository as booking_repository
import scheduling.application.ports.slot_directory as slot_directory
import scheduling.application.views as views
import scheduling.client.client as client
import scheduling.domain.scheduling as domain


class BookingService(ts.ApplicationService):

    def __init__(
        self, directory: slot_directory.SlotDirectory, repository: booking_repository.BookingRepository
    ) -> None:
        self._directory = directory
        self._repository = repository

    def begin(self, request: client.BeginBookingRequest) -> client.BookingStateResponse:
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=request.booking_id))
        booking = views.began(found)
        self._repository.save(views.save_request(request.booking_id, booking))  # tessercheck:ignore TB082
        return views.state(booking, views.begin_reply(found))  # tessercheck:ignore TB082

    def provide_name(self, request: client.ProvideNameRequest) -> client.BookingStateResponse:
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=request.booking_id))
        booking = views.loaded(found)
        available = self._directory.available(slot_directory.AvailableSlotsRequest())
        offered = tuple(domain.Slot(label) for label in available.slots)
        booking.provide_name(domain.CustomerName(request.name), offered)
        self._repository.save(views.save_request(request.booking_id, booking))  # tessercheck:ignore TB082
        return views.state(booking, "offer the caller the available slots")

    def choose_slot(self, request: client.ChooseSlotRequest) -> client.BookingStateResponse:
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=request.booking_id))
        booking = views.loaded(found)
        booking.choose_slot(domain.Slot(request.slot))
        self._repository.save(views.save_request(request.booking_id, booking))  # tessercheck:ignore TB082
        return views.state(booking, f"slot {booking.chosen()} selected; ask the caller to confirm")

    def confirm(self, request: client.ConfirmBookingRequest) -> client.BookingStateResponse:
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=request.booking_id))
        booking = views.loaded(found)
        booking.confirm()
        slot, name = str(booking.chosen()), str(booking.name())  # tessercheck:ignore TB082
        reserved = self._directory.reserve(slot_directory.ReserveSlotRequest(slot=slot, name=name))
        settled = views.confirmed(reserved, booking, views.only(found))  # tessercheck:ignore TB082
        self._repository.save(views.save_request(request.booking_id, settled))  # tessercheck:ignore TB082
        return views.state(settled, views.confirm_reply(reserved, booking))  # tessercheck:ignore TB082

    def status(self, request: client.StatusRequest) -> client.BookingStateResponse:
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=request.booking_id))
        return views.state(views.loaded(found), "continue the booking")  # tessercheck:ignore TB082
