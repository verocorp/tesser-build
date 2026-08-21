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
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        booking = views.began(found)
        save_booking_request = views.save_request(booking_id_text, booking)
        self._repository.save(save_booking_request)
        begin_reply = views.begin_reply(found)
        return views.state(booking, begin_reply)

    def provide_name(self, request: client.ProvideNameRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        booking = views.loaded(found)
        available = self._directory.available(slot_directory.AvailableSlotsRequest())
        offered = tuple(domain.Slot(label) for label in available.slots)
        booking.provide_name(domain.CustomerName(request.name), offered)
        save_booking_request = views.save_request(booking_id_text, booking)
        self._repository.save(save_booking_request)
        return views.state(booking, "offer the caller the available slots")

    def choose_slot(self, request: client.ChooseSlotRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        booking = views.loaded(found)
        booking.choose_slot(domain.Slot(request.slot))
        save_booking_request = views.save_request(booking_id_text, booking)
        self._repository.save(save_booking_request)
        return views.state(booking, f"slot {booking.chosen()} selected; ask the caller to confirm")

    def confirm(self, request: client.ConfirmBookingRequest) -> client.BookingStateResponse:  # tesser:debt TB082
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        booking = views.loaded(found)
        booking.confirm()
        chosen_slot = booking.chosen()
        customer_name = booking.name()
        slot, name = str(chosen_slot), str(customer_name)
        reserved = self._directory.reserve(slot_directory.ReserveSlotRequest(slot=slot, name=name))
        only = views.only(found)
        settled = views.confirmed(reserved, booking, only)
        save_booking_request = views.save_request(booking_id_text, settled)
        self._repository.save(save_booking_request)
        confirm_reply = views.confirm_reply(reserved, booking)
        return views.state(settled, confirm_reply)

    def status(self, request: client.StatusRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        loaded = views.loaded(found)
        return views.state(loaded, "continue the booking")
