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
        stored_name = booking.name()
        stored_chosen = booking.chosen()
        stored_step = booking.step()
        stored_step_text = str(stored_step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        save_booking_request = booking_repository.SaveBookingRequest(
            booking_id=booking_id_text,
            step=stored_step_text,
            name="" if stored_name is None else str(stored_name),
            chosen="" if stored_chosen is None else str(stored_chosen),
            offered=offered_slots,
        )
        self._repository.save(save_booking_request)
        begin_reply = views.begin_reply(found)
        return client.BookingStateResponse(
            step=stored_step_text, offered_slots=offered_slots, reply=begin_reply
        )

    def provide_name(self, request: client.ProvideNameRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        booking = views.loaded(found)
        available = self._directory.available(slot_directory.AvailableSlotsRequest())
        offered = tuple(domain.Slot(label) for label in available.slots)
        booking.provide_name(domain.CustomerName(request.name), offered)
        stored_name = booking.name()
        stored_chosen = booking.chosen()
        stored_step = booking.step()
        stored_step_text = str(stored_step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        save_booking_request = booking_repository.SaveBookingRequest(
            booking_id=booking_id_text,
            step=stored_step_text,
            name="" if stored_name is None else str(stored_name),
            chosen="" if stored_chosen is None else str(stored_chosen),
            offered=offered_slots,
        )
        self._repository.save(save_booking_request)
        return client.BookingStateResponse(
            step=stored_step_text,
            offered_slots=offered_slots,
            reply="offer the caller the available slots",
        )

    def choose_slot(self, request: client.ChooseSlotRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        booking = views.loaded(found)
        booking.choose_slot(domain.Slot(request.slot))
        stored_name = booking.name()
        stored_chosen = booking.chosen()
        stored_step = booking.step()
        stored_step_text = str(stored_step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        save_booking_request = booking_repository.SaveBookingRequest(
            booking_id=booking_id_text,
            step=stored_step_text,
            name="" if stored_name is None else str(stored_name),
            chosen="" if stored_chosen is None else str(stored_chosen),
            offered=offered_slots,
        )
        self._repository.save(save_booking_request)
        return client.BookingStateResponse(
            step=stored_step_text,
            offered_slots=offered_slots,
            reply=f"slot {booking.chosen()} selected; ask the caller to confirm",
        )

    def confirm(self, request: client.ConfirmBookingRequest) -> client.BookingStateResponse:
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
        stored_name = settled.name()
        stored_chosen = settled.chosen()
        stored_step = settled.step()
        stored_step_text = str(stored_step)
        stored_offered = settled.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        save_booking_request = booking_repository.SaveBookingRequest(
            booking_id=booking_id_text,
            step=stored_step_text,
            name="" if stored_name is None else str(stored_name),
            chosen="" if stored_chosen is None else str(stored_chosen),
            offered=offered_slots,
        )
        self._repository.save(save_booking_request)
        confirm_reply = views.confirm_reply(reserved, booking)
        return client.BookingStateResponse(
            step=stored_step_text, offered_slots=offered_slots, reply=confirm_reply
        )

    def status(self, request: client.StatusRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        loaded = views.loaded(found)
        loaded_step = loaded.step()
        loaded_step_text = str(loaded_step)
        loaded_offered = loaded.offered()
        offered_slots = tuple(str(slot) for slot in loaded_offered)
        return client.BookingStateResponse(
            step=loaded_step_text, offered_slots=offered_slots, reply="continue the booking"
        )
