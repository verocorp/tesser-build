from __future__ import annotations

import typing

import tesser.application as ts

import scheduling.application.ports as ports
import scheduling.client as client
import scheduling.domain as domain


class MapToFindBookingRequest(ts.Mapper, ports.FindBookingRequest):

    def __init__(self, booking_id: domain.BookingID) -> None:
        super().__init__(booking_id=str(booking_id))


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


class MapToReserveSlotRequest(ts.Mapper, ports.ReserveSlotRequest):

    def __init__(
        self, slot: domain.Slot | None, customer_name: domain.CustomerName | None
    ) -> None:
        super().__init__(slot=str(slot), name=str(customer_name))


class MapToBookingStateResponseAskingName(ts.Mapper, client.BookingStateResponse):

    def __init__(self, booking: domain.Booking) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(slot) for slot in booking.offered()),
            reply="ask the caller for their name",
        )


class MapToBookingStateResponseContinuing(ts.Mapper, client.BookingStateResponse):

    def __init__(self, booking: domain.Booking) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(slot) for slot in booking.offered()),
            reply="continue the booking",
        )


class MapToBookingStateResponseOfferingSlots(ts.Mapper, client.BookingStateResponse):

    def __init__(self, booking: domain.Booking) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(slot) for slot in booking.offered()),
            reply="offer the caller the available slots",
        )


class MapToBookingStateResponseAwaitingConfirmation(ts.Mapper, client.BookingStateResponse):

    def __init__(self, booking: domain.Booking) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(slot) for slot in booking.offered()),
            reply=f"slot {booking.chosen()} selected; ask the caller to confirm",
        )


class MapToBookingStateResponseBooked(ts.Mapper, client.BookingStateResponse):

    def __init__(
        self, booking: domain.Booking, slot: domain.Slot | None, customer_name: domain.CustomerName | None
    ) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(slot) for slot in booking.offered()),
            reply=f"booked {slot} for {customer_name}",
        )


class MapToBookingStateResponseReoffered(ts.Mapper, client.BookingStateResponse):

    def __init__(self, booking: domain.Booking, slot: domain.Slot | None) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(offered) for offered in booking.offered()),
            reply=f"{slot} was just taken; offer the caller the updated slots",
        )


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
        find_booking_response = self._booking_repository.find(
            MapToFindBookingRequest(booking_id)
        )
        booking = domain.Booking(MapToBegunBookingSpec(find_booking_response))
        self._booking_repository.save(MapToSaveBookingRequest(booking, booking_id))
        resumption = domain.Resumption(MapToResumptionSpec(find_booking_response))
        match resumption.resumed():
            case domain.Resumed.RESUMED:
                return MapToBookingStateResponseContinuing(booking)
            case domain.Resumed.STARTED:
                return MapToBookingStateResponseAskingName(booking)
            case _ as unreachable:
                typing.assert_never(unreachable)

    def provide_name(
        self, provide_name_request: client.ProvideNameRequest
    ) -> client.BookingStateResponse:
        booking_id = domain.BookingID(provide_name_request.booking_id)
        find_booking_response = self._booking_repository.find(
            MapToFindBookingRequest(booking_id)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        available_slots_response = self._slot_directory.available(
            ports.AvailableSlotsRequest()
        )
        booking.provide_name(
            MapToNamingSpec(provide_name_request, available_slots_response)
        )
        self._booking_repository.save(MapToSaveBookingRequest(booking, booking_id))
        return MapToBookingStateResponseOfferingSlots(booking)

    def choose_slot(
        self, choose_slot_request: client.ChooseSlotRequest
    ) -> client.BookingStateResponse:
        booking_id = domain.BookingID(choose_slot_request.booking_id)
        find_booking_response = self._booking_repository.find(
            MapToFindBookingRequest(booking_id)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        booking.choose_slot(domain.Slot(choose_slot_request.slot))
        self._booking_repository.save(MapToSaveBookingRequest(booking, booking_id))
        return MapToBookingStateResponseAwaitingConfirmation(booking)

    def confirm(
        self, confirm_booking_request: client.ConfirmBookingRequest
    ) -> client.BookingStateResponse:
        booking_id = domain.BookingID(confirm_booking_request.booking_id)
        find_booking_response = self._booking_repository.find(
            MapToFindBookingRequest(booking_id)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        booking.confirm()
        chosen_slot = booking.chosen()
        customer_name = booking.name()
        reserve_slot_response = self._slot_directory.reserve(
            MapToReserveSlotRequest(chosen_slot, customer_name)
        )
        settled = booking.settle(domain.Reoffers(MapToReoffersSpec(reserve_slot_response)))
        self._booking_repository.save(MapToSaveBookingRequest(booking, booking_id))
        match settled:
            case domain.Settled.BOOKED:
                return MapToBookingStateResponseBooked(booking, chosen_slot, customer_name)
            case domain.Settled.REOFFERED:
                return MapToBookingStateResponseReoffered(booking, chosen_slot)
            case _ as unreachable:
                typing.assert_never(unreachable)

    def status(self, status_request: client.StatusRequest) -> client.BookingStateResponse:
        booking_id = domain.BookingID(status_request.booking_id)
        find_booking_response = self._booking_repository.find(
            MapToFindBookingRequest(booking_id)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        return MapToBookingStateResponseContinuing(booking)
