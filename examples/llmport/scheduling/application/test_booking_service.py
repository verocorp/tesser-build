from __future__ import annotations

import pytest
import tesser.testing as ts

import scheduling.application as application
import scheduling.application.ports as ports
import scheduling.client as client
import scheduling.domain as domain


@ts.fake
class FakeSlotDirectory(ports.SlotDirectory):

    def __init__(self, slots: tuple[str, ...]) -> None:
        self.slots = list(slots)
        self.reserved: list[tuple[str, str]] = []

    def available(
        self, available_slots_request: ports.AvailableSlotsRequest
    ) -> ports.AvailableSlotsResponse:
        return ports.AvailableSlotsResponse(slots=tuple(self.slots))

    def reserve(
        self, reserve_slot_request: ports.ReserveSlotRequest
    ) -> ports.ReserveSlotResponse:
        if reserve_slot_request.slot not in self.slots:
            return ports.ReserveSlotResponse(
                outcome=ports.ReservationOutcome.SLOT_TAKEN, available=tuple(self.slots)
            )
        self.slots.remove(reserve_slot_request.slot)
        self.reserved.append((reserve_slot_request.slot, reserve_slot_request.name))
        return ports.ReserveSlotResponse(
            outcome=ports.ReservationOutcome.RESERVED, available=()
        )


@ts.fake
class FakeBookingRepository(ports.BookingRepository):

    def __init__(self) -> None:
        self.stored: dict[str, ports.BookingView] = {}

    def find(
        self, find_booking_request: ports.FindBookingRequest
    ) -> ports.FindBookingResponse:
        row = self.stored.get(find_booking_request.booking_id)
        if row is None:
            return ports.FindBookingResponse(
                presence=ports.BookingPresence.ABSENT, bookings=()
            )
        return ports.FindBookingResponse(
            presence=ports.BookingPresence.PRESENT, bookings=(row,)
        )

    def save(
        self, save_booking_request: ports.SaveBookingRequest
    ) -> ports.SaveBookingResponse:
        self.stored[save_booking_request.booking_id] = ports.BookingView(
            step=save_booking_request.step,
            name=save_booking_request.name,
            chosen=save_booking_request.chosen,
            offered=save_booking_request.offered,
        )
        return ports.SaveBookingResponse()


@ts.fake
class FakeSlotDirectoryDown(ports.SlotDirectory):

    def available(
        self, available_slots_request: ports.AvailableSlotsRequest
    ) -> ports.AvailableSlotsResponse:
        raise RuntimeError("slot directory unreachable")

    def reserve(
        self, reserve_slot_request: ports.ReserveSlotRequest
    ) -> ports.ReserveSlotResponse:
        raise RuntimeError("slot directory unreachable")


def test_the_full_booking_flow_through_the_client_surface() -> None:
    fake_slot_directory = FakeSlotDirectory(("mon-9am", "tue-2pm"))
    fake_booking_repository = FakeBookingRepository()
    booking_service = application.BookingService(
        fake_slot_directory, fake_booking_repository
    )

    booking_state_response = booking_service.begin(
        client.BeginBookingRequest(booking_id="b1")
    )
    assert isinstance(booking_state_response, client.BookingStateResponse)
    assert booking_state_response.step == "collect_name"
    assert booking_state_response.reply == "ask the caller for their name"
    assert fake_booking_repository.stored["b1"].name == ""
    assert fake_booking_repository.stored["b1"].chosen == ""
    assert fake_booking_repository.stored["b1"].offered == ()

    booking_state_response = booking_service.provide_name(
        client.ProvideNameRequest(booking_id="b1", name="Ada Lovelace")
    )
    assert booking_state_response.step == "choose_slot"
    assert booking_state_response.offered_slots == ("mon-9am", "tue-2pm")

    booking_state_response = booking_service.choose_slot(
        client.ChooseSlotRequest(booking_id="b1", slot="mon-9am")
    )
    assert booking_state_response.step == "confirm"

    booking_state_response = booking_service.confirm(
        client.ConfirmBookingRequest(booking_id="b1")
    )
    assert booking_state_response.step == "booked"
    assert booking_state_response.reply == "booked mon-9am for Ada Lovelace"
    assert fake_slot_directory.reserved == [("mon-9am", "Ada Lovelace")]
    assert fake_booking_repository.stored["b1"].step == "booked"
    assert fake_booking_repository.stored["b1"].name == "Ada Lovelace"
    assert fake_booking_repository.stored["b1"].chosen == "mon-9am"


def test_a_rejected_transition_persists_nothing() -> None:
    fake_slot_directory = FakeSlotDirectory(("mon-9am",))
    fake_booking_repository = FakeBookingRepository()
    booking_service = application.BookingService(
        fake_slot_directory, fake_booking_repository
    )
    booking_service.begin(client.BeginBookingRequest(booking_id="b1"))
    booking_service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))

    with pytest.raises(ValueError):
        booking_service.choose_slot(
            client.ChooseSlotRequest(booking_id="b1", slot="wed-4pm")
        )

    assert fake_booking_repository.stored["b1"].step == "choose_slot"
    assert fake_booking_repository.stored["b1"].chosen == ""


def test_a_slot_taken_between_choice_and_confirm_comes_back_as_a_fresh_offer() -> None:
    fake_slot_directory = FakeSlotDirectory(("mon-9am", "tue-2pm"))
    fake_booking_repository = FakeBookingRepository()
    booking_service = application.BookingService(
        fake_slot_directory, fake_booking_repository
    )
    booking_service.begin(client.BeginBookingRequest(booking_id="b1"))
    booking_service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))
    booking_service.choose_slot(client.ChooseSlotRequest(booking_id="b1", slot="mon-9am"))

    fake_slot_directory.slots.remove("mon-9am")
    booking_state_response = booking_service.confirm(
        client.ConfirmBookingRequest(booking_id="b1")
    )

    assert booking_state_response.reply == (
        "mon-9am was just taken; offer the caller the updated slots"
    )
    assert booking_state_response.step == "choose_slot"
    assert booking_state_response.offered_slots == ("tue-2pm",)
    assert fake_booking_repository.stored["b1"].step == "choose_slot"
    assert fake_booking_repository.stored["b1"].offered == ("tue-2pm",)


def test_a_taken_slot_with_nothing_left_to_offer_is_an_error() -> None:
    fake_slot_directory = FakeSlotDirectory(("mon-9am",))
    booking_service = application.BookingService(
        fake_slot_directory, FakeBookingRepository()
    )
    booking_service.begin(client.BeginBookingRequest(booking_id="b1"))
    booking_service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))
    booking_service.choose_slot(client.ChooseSlotRequest(booking_id="b1", slot="mon-9am"))

    fake_slot_directory.slots.remove("mon-9am")
    with pytest.raises(ValueError) as excinfo:
        booking_service.confirm(client.ConfirmBookingRequest(booking_id="b1"))

    assert "no slots are available" in str(excinfo.value)


def test_the_fresh_offer_is_choosable_and_bookable() -> None:
    fake_slot_directory = FakeSlotDirectory(("mon-9am", "tue-2pm"))
    booking_service = application.BookingService(
        fake_slot_directory, FakeBookingRepository()
    )
    booking_service.begin(client.BeginBookingRequest(booking_id="b1"))
    booking_service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))
    booking_service.choose_slot(client.ChooseSlotRequest(booking_id="b1", slot="mon-9am"))
    fake_slot_directory.slots.remove("mon-9am")
    booking_service.confirm(client.ConfirmBookingRequest(booking_id="b1"))

    booking_service.choose_slot(client.ChooseSlotRequest(booking_id="b1", slot="tue-2pm"))
    booking_state_response = booking_service.confirm(
        client.ConfirmBookingRequest(booking_id="b1")
    )

    assert booking_state_response.step == "booked"
    assert fake_slot_directory.reserved == [("tue-2pm", "Ada")]


def test_status_reads_without_mutating() -> None:
    fake_slot_directory = FakeSlotDirectory(("mon-9am",))
    fake_booking_repository = FakeBookingRepository()
    booking_service = application.BookingService(
        fake_slot_directory, fake_booking_repository
    )
    booking_service.begin(client.BeginBookingRequest(booking_id="b1"))
    booking_service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))

    booking_state_response = booking_service.status(client.StatusRequest(booking_id="b1"))

    assert booking_state_response.step == "choose_slot"
    assert booking_state_response.offered_slots == ("mon-9am",)
    assert fake_booking_repository.stored["b1"].step == "choose_slot"


def test_an_infrastructure_failure_passes_through_untranslated() -> None:
    booking_service = application.BookingService(
        FakeSlotDirectoryDown(), FakeBookingRepository()
    )
    booking_service.begin(client.BeginBookingRequest(booking_id="b1"))

    with pytest.raises(RuntimeError):
        booking_service.provide_name(
            client.ProvideNameRequest(booking_id="b1", name="Ada")
        )


def test_begin_resumes_an_in_flight_booking() -> None:
    fake_slot_directory = FakeSlotDirectory(("mon-9am",))
    fake_booking_repository = FakeBookingRepository()
    booking_service = application.BookingService(
        fake_slot_directory, fake_booking_repository
    )
    booking_service.begin(client.BeginBookingRequest(booking_id="b1"))
    booking_service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))

    booking_state_response = booking_service.begin(
        client.BeginBookingRequest(booking_id="b1")
    )

    assert booking_state_response.step == "choose_slot"
    assert booking_state_response.offered_slots == ("mon-9am",)
    assert booking_state_response.reply == "continue the booking"
    assert fake_booking_repository.stored["b1"].name == "Ada"


def test_begin_resumes_a_booked_booking_without_touching_it() -> None:
    fake_slot_directory = FakeSlotDirectory(("mon-9am",))
    fake_booking_repository = FakeBookingRepository()
    booking_service = application.BookingService(
        fake_slot_directory, fake_booking_repository
    )
    booking_service.begin(client.BeginBookingRequest(booking_id="b1"))
    booking_service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))
    booking_service.choose_slot(client.ChooseSlotRequest(booking_id="b1", slot="mon-9am"))
    booking_service.confirm(client.ConfirmBookingRequest(booking_id="b1"))

    booking_state_response = booking_service.begin(
        client.BeginBookingRequest(booking_id="b1")
    )

    assert booking_state_response.step == "booked"
    assert fake_booking_repository.stored["b1"].step == "booked"
    assert fake_slot_directory.reserved == [("mon-9am", "Ada")]


def test_an_unknown_booking_id_is_not_a_domain_rejection() -> None:
    booking_service = application.BookingService(
        FakeSlotDirectory(("mon-9am",)), FakeBookingRepository()
    )

    with pytest.raises(KeyError):
        booking_service.status(client.StatusRequest(booking_id="ghost"))


def test_an_empty_booking_id_is_refused_before_the_repository_is_read() -> None:
    fake_booking_repository = FakeBookingRepository()
    booking_service = application.BookingService(
        FakeSlotDirectory(("mon-9am",)), fake_booking_repository
    )
    with pytest.raises(ValueError, match="booking id must be non-empty"):
        booking_service.begin(client.BeginBookingRequest(booking_id=""))
    assert fake_booking_repository.stored == {}


def test_the_mapper_exposes_every_field_of_the_one_row_the_repository_found() -> None:
    find_booking_response = ports.FindBookingResponse(
        presence=ports.BookingPresence.PRESENT,
        bookings=(
            ports.BookingView(
                step="confirm",
                name="Ada Lovelace",
                chosen="mon-9am",
                offered=("mon-9am", "tue-2pm"),
            ),
        ),
    )

    map_to_booking_spec = application.MapToBookingSpec(find_booking_response)

    assert map_to_booking_spec.step == "confirm"
    assert map_to_booking_spec.name == "Ada Lovelace"
    assert map_to_booking_spec.chosen == "mon-9am"
    assert map_to_booking_spec.offered == ("mon-9am", "tue-2pm")


def test_the_mapper_refuses_a_booking_the_repository_does_not_hold() -> None:
    find_booking_response = ports.FindBookingResponse(
        presence=ports.BookingPresence.ABSENT, bookings=()
    )

    with pytest.raises(KeyError):
        application.MapToBookingSpec(find_booking_response)


def test_the_begun_mapper_opens_a_fresh_booking_when_none_is_stored() -> None:
    find_booking_response = ports.FindBookingResponse(
        presence=ports.BookingPresence.ABSENT, bookings=()
    )

    map_to_begun_booking_spec = application.MapToBegunBookingSpec(find_booking_response)

    assert map_to_begun_booking_spec.step == "collect_name"
    assert map_to_begun_booking_spec.name == ""
    assert map_to_begun_booking_spec.chosen == ""
    assert map_to_begun_booking_spec.offered == ()


def test_the_begun_mapper_resumes_the_booking_already_stored() -> None:
    find_booking_response = ports.FindBookingResponse(
        presence=ports.BookingPresence.PRESENT,
        bookings=(
            ports.BookingView(
                step="choose_slot", name="Ada", chosen="", offered=("mon-9am",)
            ),
        ),
    )

    map_to_begun_booking_spec = application.MapToBegunBookingSpec(find_booking_response)

    assert map_to_begun_booking_spec.step == "choose_slot"
    assert map_to_begun_booking_spec.name == "Ada"
    assert map_to_begun_booking_spec.chosen == ""
    assert map_to_begun_booking_spec.offered == ("mon-9am",)


def test_a_stored_booking_maps_to_a_resumption_that_resumes() -> None:
    find_booking_response = ports.FindBookingResponse(
        presence=ports.BookingPresence.PRESENT,
        bookings=(
            ports.BookingView(
                step="choose_slot", name="Ada", chosen="", offered=("mon-9am",)
            ),
        ),
    )

    resumption = domain.Resumption(
        application.MapToResumptionSpec(find_booking_response)
    )

    assert resumption.resumed() is domain.Resumed.RESUMED


def test_a_booking_the_repository_does_not_hold_maps_to_a_resumption_that_starts() -> None:
    find_booking_response = ports.FindBookingResponse(
        presence=ports.BookingPresence.ABSENT, bookings=()
    )

    resumption = domain.Resumption(
        application.MapToResumptionSpec(find_booking_response)
    )

    assert resumption.resumed() is domain.Resumed.STARTED


def test_a_reserved_slot_hands_the_booking_no_reoffer_at_all() -> None:
    reserve_slot_response = ports.ReserveSlotResponse(
        outcome=ports.ReservationOutcome.RESERVED, available=()
    )

    map_to_reoffers_spec = application.MapToReoffersSpec(reserve_slot_response)

    assert map_to_reoffers_spec.offered == ()


def test_a_taken_slot_hands_the_booking_one_reoffer_of_the_slots_still_open() -> None:
    reserve_slot_response = ports.ReserveSlotResponse(
        outcome=ports.ReservationOutcome.SLOT_TAKEN, available=("tue-2pm",)
    )

    map_to_reoffers_spec = application.MapToReoffersSpec(reserve_slot_response)

    assert map_to_reoffers_spec.offered == (("tue-2pm",),)


def test_a_taken_slot_with_nothing_open_still_hands_the_booking_a_reoffer() -> None:
    reserve_slot_response = ports.ReserveSlotResponse(
        outcome=ports.ReservationOutcome.SLOT_TAKEN, available=()
    )

    map_to_reoffers_spec = application.MapToReoffersSpec(reserve_slot_response)

    assert map_to_reoffers_spec.offered == ((),)


def test_a_reserved_slot_leaves_the_confirmed_booking_alone() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="booked", name="Ada", chosen="mon-9am", offered=("mon-9am",))
    )

    booking.settle(domain.Reoffers(domain.ReoffersSpec(offered=())))

    assert str(booking.step()) == "booked"
    assert str(booking.chosen()) == "mon-9am"


def test_a_taken_slot_sends_the_booking_back_to_choosing_from_the_new_offer() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="booked", name="Ada", chosen="mon-9am", offered=("mon-9am",))
    )

    booking.settle(domain.Reoffers(domain.ReoffersSpec(offered=(("tue-2pm",),))))

    assert str(booking.step()) == "choose_slot"
    assert booking.chosen() is None
    assert tuple(str(slot) for slot in booking.offered()) == ("tue-2pm",)


def test_a_reserved_slot_settles_the_booking_as_booked() -> None:
    booking = domain.Booking(
        domain.BookingSpec(
            step="booked", name="Ada Lovelace", chosen="mon-9am", offered=("mon-9am",)
        )
    )
    reserve_slot_response = ports.ReserveSlotResponse(
        outcome=ports.ReservationOutcome.RESERVED, available=()
    )

    settled = booking.settle(
        domain.Reoffers(application.MapToReoffersSpec(reserve_slot_response))
    )

    assert settled is domain.Settled.BOOKED


def test_a_taken_slot_settles_the_booking_as_reoffered() -> None:
    booking = domain.Booking(
        domain.BookingSpec(
            step="booked", name="Ada Lovelace", chosen="mon-9am", offered=("mon-9am",)
        )
    )
    reserve_slot_response = ports.ReserveSlotResponse(
        outcome=ports.ReservationOutcome.SLOT_TAKEN, available=("tue-2pm",)
    )

    settled = booking.settle(
        domain.Reoffers(application.MapToReoffersSpec(reserve_slot_response))
    )

    assert settled is domain.Settled.REOFFERED


def test_a_provide_name_request_maps_to_a_naming_of_the_slots_still_open() -> None:
    map_to_naming_spec = application.MapToNamingSpec(
        client.ProvideNameRequest(booking_id="b-1", name="Ada"),
        ports.AvailableSlotsResponse(slots=("mon-9am", "tue-2pm")),
    )

    assert map_to_naming_spec.name == "Ada"
    assert map_to_naming_spec.offered.labels == ("mon-9am", "tue-2pm")


def test_a_booking_that_has_not_been_named_yet_saves_a_blank_name_and_choice() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )

    map_to_save_booking_request = application.MapToSaveBookingRequest(
        booking, domain.BookingID("b-1")
    )

    assert map_to_save_booking_request.booking_id == "b-1"
    assert map_to_save_booking_request.step == "collect_name"
    assert map_to_save_booking_request.name == ""
    assert map_to_save_booking_request.chosen == ""
    assert map_to_save_booking_request.offered == ()


def test_a_booking_that_chose_a_slot_saves_the_name_the_choice_and_the_offer() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )
    booking.provide_name(
        domain.NamingSpec(name="Ada", offered=domain.OfferSpec(labels=("mon-9am", "tue-2pm")))
    )
    booking.choose_slot(domain.Slot("mon-9am"))

    map_to_save_booking_request = application.MapToSaveBookingRequest(
        booking, domain.BookingID("b-1")
    )

    assert map_to_save_booking_request.step == "confirm"
    assert map_to_save_booking_request.name == "Ada"
    assert map_to_save_booking_request.chosen == "mon-9am"
    assert map_to_save_booking_request.offered == ("mon-9am", "tue-2pm")
