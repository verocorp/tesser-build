from __future__ import annotations

import typing

import tesser.application as ts

import scheduling.application.ports as ports
import scheduling.client as client
import scheduling.domain as domain


class MapToBookingSpec(ts.Mapper, domain.BookingSpec):

    def __init__(self, find_booking_response: ports.FindBookingResponse) -> None:
        match find_booking_response.presence:
            case ports.BookingPresence.PRESENT:
                view = find_booking_response.bookings[0]
            case ports.BookingPresence.ABSENT:
                raise KeyError("booking not found")
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(
            step=view.step, name=view.name, chosen=view.chosen, offered=view.offered
        )


class MapToBegunBookingSpec(ts.Mapper, domain.BookingSpec):

    def __init__(self, find_booking_response: ports.FindBookingResponse) -> None:
        step = domain.COLLECT_NAME
        name = ""
        chosen = ""
        offered: tuple[str, ...] = ()
        match find_booking_response.presence:
            case ports.BookingPresence.PRESENT:
                view = find_booking_response.bookings[0]
                step, name, chosen, offered = view.step, view.name, view.chosen, view.offered
            case ports.BookingPresence.ABSENT:
                pass
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(step=step, name=name, chosen=chosen, offered=offered)


class MapToResumptionSpec(ts.Mapper, domain.ResumptionSpec):

    def __init__(self, find_booking_response: ports.FindBookingResponse) -> None:
        super().__init__(presence=find_booking_response.presence.value)


class MapToNamingSpec(ts.Mapper, domain.NamingSpec):

    def __init__(
        self,
        provide_name_request: client.ProvideNameRequest,
        available_slots_response: ports.AvailableSlotsResponse,
    ) -> None:
        super().__init__(
            name=provide_name_request.name,
            offered=domain.OfferSpec(labels=available_slots_response.slots),
        )


class MapToSaveBookingRequest(ts.Mapper, ports.SaveBookingRequest):

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

    def __init__(self, reserve_slot_response: ports.ReserveSlotResponse) -> None:
        offered: tuple[tuple[str, ...], ...] = ()
        match reserve_slot_response.outcome:
            case ports.ReservationOutcome.RESERVED:
                pass
            case ports.ReservationOutcome.SLOT_TAKEN:
                offered = (reserve_slot_response.available,)
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(offered=offered)


class BookingService(ts.ApplicationService):

    def __init__(
        self, slot_directory: ports.SlotDirectory, booking_repository: ports.BookingRepository
    ) -> None:
        self._slot_directory = slot_directory
        self._booking_repository = booking_repository

    def begin(
        self, begin_booking_request: client.BeginBookingRequest
    ) -> client.BookingStateResponse:
        booking_id = domain.BookingID(begin_booking_request.booking_id)
        booking_id_text = str(booking_id)
        find_booking_response = self._booking_repository.find(
            ports.FindBookingRequest(booking_id=booking_id_text)
        )
        booking = domain.Booking(MapToBegunBookingSpec(find_booking_response))
        step = booking.step()
        step_text = str(step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        self._booking_repository.save(MapToSaveBookingRequest(booking, booking_id))
        resumption = domain.Resumption(MapToResumptionSpec(find_booking_response))
        begin_reply = ""
        match resumption.resumed():
            case domain.Resumed.RESUMED:
                begin_reply = "continue the booking"
            case domain.Resumed.STARTED:
                begin_reply = "ask the caller for their name"
            case _ as unreachable:
                typing.assert_never(unreachable)
        return client.BookingStateResponse(
            step=step_text, offered_slots=offered_slots, reply=begin_reply
        )

    def provide_name(
        self, provide_name_request: client.ProvideNameRequest
    ) -> client.BookingStateResponse:
        booking_id = domain.BookingID(provide_name_request.booking_id)
        booking_id_text = str(booking_id)
        find_booking_response = self._booking_repository.find(
            ports.FindBookingRequest(booking_id=booking_id_text)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        available_slots_response = self._slot_directory.available(
            ports.AvailableSlotsRequest()
        )
        booking.provide_name(
            MapToNamingSpec(provide_name_request, available_slots_response)
        )
        step = booking.step()
        step_text = str(step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        self._booking_repository.save(MapToSaveBookingRequest(booking, booking_id))
        return client.BookingStateResponse(
            step=step_text,
            offered_slots=offered_slots,
            reply="offer the caller the available slots",
        )

    def choose_slot(
        self, choose_slot_request: client.ChooseSlotRequest
    ) -> client.BookingStateResponse:
        booking_id = domain.BookingID(choose_slot_request.booking_id)
        booking_id_text = str(booking_id)
        find_booking_response = self._booking_repository.find(
            ports.FindBookingRequest(booking_id=booking_id_text)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        booking.choose_slot(domain.Slot(choose_slot_request.slot))
        step = booking.step()
        step_text = str(step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        self._booking_repository.save(MapToSaveBookingRequest(booking, booking_id))
        return client.BookingStateResponse(
            step=step_text,
            offered_slots=offered_slots,
            reply=f"slot {booking.chosen()} selected; ask the caller to confirm",
        )

    def confirm(
        self, confirm_booking_request: client.ConfirmBookingRequest
    ) -> client.BookingStateResponse:
        booking_id = domain.BookingID(confirm_booking_request.booking_id)
        booking_id_text = str(booking_id)
        find_booking_response = self._booking_repository.find(
            ports.FindBookingRequest(booking_id=booking_id_text)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        booking.confirm()
        chosen_slot = booking.chosen()
        customer_name = booking.name()
        slot, name = str(chosen_slot), str(customer_name)
        reserve_slot_response = self._slot_directory.reserve(
            ports.ReserveSlotRequest(slot=slot, name=name)
        )
        confirm_reply = ""
        match booking.settle(domain.Reoffers(MapToReoffersSpec(reserve_slot_response))):
            case domain.Settled.BOOKED:
                confirm_reply = f"booked {slot} for {name}"
            case domain.Settled.REOFFERED:
                confirm_reply = f"{slot} was just taken; offer the caller the updated slots"
            case _ as unreachable:
                typing.assert_never(unreachable)
        step = booking.step()
        step_text = str(step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        self._booking_repository.save(MapToSaveBookingRequest(booking, booking_id))
        return client.BookingStateResponse(
            step=step_text, offered_slots=offered_slots, reply=confirm_reply
        )

    def status(self, status_request: client.StatusRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(status_request.booking_id)
        booking_id_text = str(booking_id)
        find_booking_response = self._booking_repository.find(
            ports.FindBookingRequest(booking_id=booking_id_text)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        step = booking.step()
        step_text = str(step)
        stored_offered = booking.offered()
        offered_slots = tuple(str(slot) for slot in stored_offered)
        return client.BookingStateResponse(
            step=step_text, offered_slots=offered_slots, reply="continue the booking"
        )
