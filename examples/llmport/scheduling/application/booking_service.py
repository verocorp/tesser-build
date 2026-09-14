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
        match find_booking_response.outcome:
            case ports.FindBookingOutcome.PRESENT:
                view = find_booking_response.bookings[0]
            case ports.FindBookingOutcome.ABSENT:
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
        match find_booking_response.outcome:
            case ports.FindBookingOutcome.PRESENT:
                view = find_booking_response.bookings[0]
                step, name, chosen, offered = view.step, view.name, view.chosen, view.offered
            case ports.FindBookingOutcome.ABSENT:
                pass
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(step=step, name=name, chosen=chosen, offered=offered)


class MapToResumptionSpec(ts.Mapper, domain.ResumptionSpec):

    def __init__(self, find_booking_response: ports.FindBookingResponse) -> None:
        super().__init__(presence=find_booking_response.outcome.value)


class MapToNamingSpec(ts.Mapper, domain.NamingSpec):

    def __init__(
        self,
        provide_name_request: client.ProvideNameRequest,
        list_available_slots_response: ports.ListAvailableSlotsResponse,
    ) -> None:
        super().__init__(
            name=provide_name_request.name,
            offered=domain.OfferSpec(labels=list_available_slots_response.slots),
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
            case ports.ReserveSlotOutcome.RESERVED:
                pass
            case ports.ReserveSlotOutcome.SLOT_TAKEN:
                offered = (reserve_slot_response.available,)
            case _ as unreachable:
                typing.assert_never(unreachable)
        super().__init__(offered=offered)


class MapToReserveSlotRequest(ts.Mapper, ports.ReserveSlotRequest):

    def __init__(
        self, slot: domain.Slot | None, customer_name: domain.CustomerName | None
    ) -> None:
        super().__init__(slot=str(slot), name=str(customer_name))


class MapToBookingAskingName(ts.Mapper, client.Booking):

    def __init__(self, booking: domain.Booking) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(slot) for slot in booking.offered()),
            reply="ask the caller for their name",
        )


class MapToBookingContinuing(ts.Mapper, client.Booking):

    def __init__(self, booking: domain.Booking) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(slot) for slot in booking.offered()),
            reply="continue the booking",
        )


class MapToBookingOfferingSlots(ts.Mapper, client.Booking):

    def __init__(self, booking: domain.Booking) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(slot) for slot in booking.offered()),
            reply="offer the caller the available slots",
        )


class MapToBookingAwaitingConfirmation(ts.Mapper, client.Booking):

    def __init__(self, booking: domain.Booking) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(slot) for slot in booking.offered()),
            reply=f"slot {booking.chosen()} selected; ask the caller to confirm",
        )


class MapToBookingBooked(ts.Mapper, client.Booking):

    def __init__(
        self, booking: domain.Booking, slot: domain.Slot | None, customer_name: domain.CustomerName | None
    ) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(slot) for slot in booking.offered()),
            reply=f"booked {slot} for {customer_name}",
        )


class MapToBookingReoffered(ts.Mapper, client.Booking):

    def __init__(self, booking: domain.Booking, slot: domain.Slot | None) -> None:
        super().__init__(
            step=str(booking.step()),
            offered_slots=tuple(str(offered) for offered in booking.offered()),
            reply=f"{slot} was just taken; offer the caller the updated slots",
        )


class MapToBeginBookingResponse(ts.Mapper, client.BeginBookingResponse):

    def __init__(self, booking: client.Booking) -> None:
        super().__init__(booking=booking)


class MapToProvideNameResponse(ts.Mapper, client.ProvideNameResponse):

    def __init__(self, booking: client.Booking) -> None:
        super().__init__(booking=booking)


class MapToChooseSlotResponse(ts.Mapper, client.ChooseSlotResponse):

    def __init__(self, booking: client.Booking) -> None:
        super().__init__(booking=booking)


class MapToConfirmBookingResponse(ts.Mapper, client.ConfirmBookingResponse):

    def __init__(self, booking: client.Booking) -> None:
        super().__init__(booking=booking)


class MapToGetBookingResponse(ts.Mapper, client.GetBookingResponse):

    def __init__(self, booking: client.Booking) -> None:
        super().__init__(booking=booking)


class BookingService(ts.ApplicationService):

    def __init__(
        self, slot_directory: ports.SlotDirectory, booking_repository: ports.BookingRepository
    ) -> None:
        self._slot_directory = slot_directory
        self._booking_repository = booking_repository

    def begin_booking(
        self, begin_booking_request: client.BeginBookingRequest
    ) -> client.BeginBookingResponse:
        booking_id = domain.BookingID(begin_booking_request.booking_id)
        find_booking_response = self._booking_repository.find_booking(
            MapToFindBookingRequest(booking_id)
        )
        booking = domain.Booking(MapToBegunBookingSpec(find_booking_response))
        self._booking_repository.save_booking(MapToSaveBookingRequest(booking, booking_id))
        resumption = domain.Resumption(MapToResumptionSpec(find_booking_response))
        match resumption.resumed():
            case domain.Resumed.RESUMED:
                return MapToBeginBookingResponse(MapToBookingContinuing(booking))
            case domain.Resumed.STARTED:
                return MapToBeginBookingResponse(MapToBookingAskingName(booking))
            case _ as unreachable:
                typing.assert_never(unreachable)

    def provide_name(
        self, provide_name_request: client.ProvideNameRequest
    ) -> client.ProvideNameResponse:
        booking_id = domain.BookingID(provide_name_request.booking_id)
        find_booking_response = self._booking_repository.find_booking(
            MapToFindBookingRequest(booking_id)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        list_available_slots_response = self._slot_directory.list_available_slots(
            ports.ListAvailableSlotsRequest()
        )
        booking.provide_name(
            MapToNamingSpec(provide_name_request, list_available_slots_response)
        )
        self._booking_repository.save_booking(MapToSaveBookingRequest(booking, booking_id))
        return MapToProvideNameResponse(MapToBookingOfferingSlots(booking))

    def choose_slot(
        self, choose_slot_request: client.ChooseSlotRequest
    ) -> client.ChooseSlotResponse:
        booking_id = domain.BookingID(choose_slot_request.booking_id)
        find_booking_response = self._booking_repository.find_booking(
            MapToFindBookingRequest(booking_id)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        booking.choose_slot(domain.Slot(choose_slot_request.slot))
        self._booking_repository.save_booking(MapToSaveBookingRequest(booking, booking_id))
        return MapToChooseSlotResponse(MapToBookingAwaitingConfirmation(booking))

    def confirm_booking(
        self, confirm_booking_request: client.ConfirmBookingRequest
    ) -> client.ConfirmBookingResponse:
        booking_id = domain.BookingID(confirm_booking_request.booking_id)
        find_booking_response = self._booking_repository.find_booking(
            MapToFindBookingRequest(booking_id)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        booking.confirm()
        chosen_slot = booking.chosen()
        customer_name = booking.name()
        reserve_slot_response = self._slot_directory.reserve_slot(
            MapToReserveSlotRequest(chosen_slot, customer_name)
        )
        settled = booking.settle(domain.Reoffers(MapToReoffersSpec(reserve_slot_response)))
        self._booking_repository.save_booking(MapToSaveBookingRequest(booking, booking_id))
        match settled:
            case domain.Settled.BOOKED:
                return MapToConfirmBookingResponse(
                    MapToBookingBooked(booking, chosen_slot, customer_name)
                )
            case domain.Settled.REOFFERED:
                return MapToConfirmBookingResponse(MapToBookingReoffered(booking, chosen_slot))
            case _ as unreachable:
                typing.assert_never(unreachable)

    def get_booking(
        self, get_booking_request: client.GetBookingRequest
    ) -> client.GetBookingResponse:
        booking_id = domain.BookingID(get_booking_request.booking_id)
        find_booking_response = self._booking_repository.find_booking(
            MapToFindBookingRequest(booking_id)
        )
        booking = domain.Booking(MapToBookingSpec(find_booking_response))
        return MapToGetBookingResponse(MapToBookingContinuing(booking))
