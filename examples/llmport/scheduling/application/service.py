from __future__ import annotations

import typing

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
        booking = domain.Booking(views.MapToBegunBookingSpec(found_booking=found))
        stored_step = booking.step()
        stored_step_text = str(stored_step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        self._repository.save(views.MapToSaveBookingRequest(booking, booking_id))
        resumption = domain.Resumption(views.MapToResumptionSpec(found_booking=found))
        begin_reply = ""
        match resumption.resumed():
            case domain.Resumed.RESUMED:
                begin_reply = "continue the booking"
            case domain.Resumed.STARTED:
                begin_reply = "ask the caller for their name"
            case _ as unreachable:
                typing.assert_never(unreachable)
        return client.BookingStateResponse(
            step=stored_step_text, offered_slots=offered_slots, reply=begin_reply
        )

    def provide_name(self, request: client.ProvideNameRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        booking = domain.Booking(views.MapToBookingSpec(found_booking=found))
        available = self._directory.available(slot_directory.AvailableSlotsRequest())
        booking.provide_name(views.MapToNamingSpec(request, available))
        stored_step = booking.step()
        stored_step_text = str(stored_step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        self._repository.save(views.MapToSaveBookingRequest(booking, booking_id))
        return client.BookingStateResponse(
            step=stored_step_text,
            offered_slots=offered_slots,
            reply="offer the caller the available slots",
        )

    def choose_slot(self, request: client.ChooseSlotRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        booking = domain.Booking(views.MapToBookingSpec(found_booking=found))
        booking.choose_slot(domain.Slot(request.slot))
        stored_step = booking.step()
        stored_step_text = str(stored_step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        self._repository.save(views.MapToSaveBookingRequest(booking, booking_id))
        return client.BookingStateResponse(
            step=stored_step_text,
            offered_slots=offered_slots,
            reply=f"slot {booking.chosen()} selected; ask the caller to confirm",
        )

    def confirm(self, request: client.ConfirmBookingRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        booking = domain.Booking(views.MapToBookingSpec(found_booking=found))
        booking.confirm()
        chosen_slot = booking.chosen()
        customer_name = booking.name()
        slot, name = str(chosen_slot), str(customer_name)
        reserved = self._directory.reserve(slot_directory.ReserveSlotRequest(slot=slot, name=name))
        confirm_reply = ""
        match booking.settle(domain.Reoffers(views.MapToReoffersSpec(reserved_slot=reserved))):
            case domain.Settled.BOOKED:
                confirm_reply = f"booked {slot} for {name}"
            case domain.Settled.REOFFERED:
                confirm_reply = f"{slot} was just taken; offer the caller the updated slots"
            case _ as unreachable:
                typing.assert_never(unreachable)
        stored_step = booking.step()
        stored_step_text = str(stored_step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        self._repository.save(views.MapToSaveBookingRequest(booking, booking_id))
        return client.BookingStateResponse(
            step=stored_step_text, offered_slots=offered_slots, reply=confirm_reply
        )

    def status(self, request: client.StatusRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(request.booking_id)
        booking_id_text = str(booking_id)
        found = self._repository.find(booking_repository.FindBookingRequest(booking_id=booking_id_text))
        loaded = domain.Booking(views.MapToBookingSpec(found_booking=found))
        loaded_step = loaded.step()
        loaded_step_text = str(loaded_step)
        loaded_offered = loaded.offered()
        offered_slots = tuple(str(slot) for slot in loaded_offered)
        return client.BookingStateResponse(
            step=loaded_step_text, offered_slots=offered_slots, reply="continue the booking"
        )
