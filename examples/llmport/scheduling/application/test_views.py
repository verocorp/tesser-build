from __future__ import annotations

import pytest

import scheduling.application.ports.booking_repository as booking_repository
import scheduling.application.ports.slot_directory as slot_directory
import scheduling.application.views as views
import scheduling.client.client as client
import scheduling.domain.scheduling as domain


def test_the_mapper_exposes_every_field_of_the_one_row_the_repository_found() -> None:
    found = booking_repository.FindBookingResponse(
        presence=booking_repository.BookingPresence.PRESENT,
        bookings=(
            booking_repository.BookingView(
                step="confirm",
                name="Ada Lovelace",
                chosen="mon-9am",
                offered=("mon-9am", "tue-2pm"),
            ),
        ),
    )

    mapper = views.MapToBookingSpec(found_booking=found)

    assert mapper.step == "confirm"
    assert mapper.name == "Ada Lovelace"
    assert mapper.chosen == "mon-9am"
    assert mapper.offered == ("mon-9am", "tue-2pm")


def test_the_mapper_refuses_a_booking_the_repository_does_not_hold() -> None:
    found = booking_repository.FindBookingResponse(
        presence=booking_repository.BookingPresence.ABSENT, bookings=()
    )

    with pytest.raises(KeyError):
        views.MapToBookingSpec(found_booking=found)


def test_began_opens_a_fresh_booking_when_none_is_stored() -> None:
    found = booking_repository.FindBookingResponse(
        presence=booking_repository.BookingPresence.ABSENT, bookings=()
    )

    booking = views.began(found)

    assert str(booking.step()) == "collect_name"
    assert booking.name() is None
    assert booking.chosen() is None
    assert booking.offered() == ()


def test_began_resumes_the_booking_already_stored() -> None:
    found = booking_repository.FindBookingResponse(
        presence=booking_repository.BookingPresence.PRESENT,
        bookings=(
            booking_repository.BookingView(
                step="choose_slot", name="Ada", chosen="", offered=("mon-9am",)
            ),
        ),
    )

    booking = views.began(found)

    assert str(booking.step()) == "choose_slot"
    assert str(booking.name()) == "Ada"


def test_beginning_a_stored_booking_tells_the_model_to_carry_on() -> None:
    found = booking_repository.FindBookingResponse(
        presence=booking_repository.BookingPresence.PRESENT,
        bookings=(
            booking_repository.BookingView(
                step="choose_slot", name="Ada", chosen="", offered=("mon-9am",)
            ),
        ),
    )

    assert views.begin_reply(found) == "continue the booking"


def test_beginning_a_new_booking_tells_the_model_to_ask_for_a_name() -> None:
    found = booking_repository.FindBookingResponse(
        presence=booking_repository.BookingPresence.ABSENT, bookings=()
    )

    assert views.begin_reply(found) == "ask the caller for their name"


def test_a_reserved_slot_hands_the_booking_no_reoffer_at_all() -> None:
    reserved = slot_directory.ReserveSlotResponse(
        outcome=slot_directory.ReservationOutcome.RESERVED, available=()
    )

    mapper = views.MapToReoffersSpec(reserved_slot=reserved)

    assert mapper.offered == ()


def test_a_taken_slot_hands_the_booking_one_reoffer_of_the_slots_still_open() -> None:
    reserved = slot_directory.ReserveSlotResponse(
        outcome=slot_directory.ReservationOutcome.SLOT_TAKEN, available=("tue-2pm",)
    )

    mapper = views.MapToReoffersSpec(reserved_slot=reserved)

    assert mapper.offered == (("tue-2pm",),)


def test_a_taken_slot_with_nothing_open_still_hands_the_booking_a_reoffer() -> None:
    reserved = slot_directory.ReserveSlotResponse(
        outcome=slot_directory.ReservationOutcome.SLOT_TAKEN, available=()
    )

    mapper = views.MapToReoffersSpec(reserved_slot=reserved)

    assert mapper.offered == ((),)


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


def test_a_reserved_slot_reads_back_as_a_booking_naming_the_caller() -> None:
    booking = domain.Booking(
        domain.BookingSpec(
            step="booked", name="Ada Lovelace", chosen="mon-9am", offered=("mon-9am",)
        )
    )
    reserved = slot_directory.ReserveSlotResponse(
        outcome=slot_directory.ReservationOutcome.RESERVED, available=()
    )

    assert views.confirm_reply(reserved, booking) == "booked mon-9am for Ada Lovelace"


def test_a_taken_slot_reads_back_as_a_prompt_to_offer_the_updated_slots() -> None:
    booking = domain.Booking(
        domain.BookingSpec(
            step="booked", name="Ada Lovelace", chosen="mon-9am", offered=("mon-9am",)
        )
    )
    reserved = slot_directory.ReserveSlotResponse(
        outcome=slot_directory.ReservationOutcome.SLOT_TAKEN, available=("tue-2pm",)
    )

    assert (
        views.confirm_reply(reserved, booking)
        == "mon-9am was just taken; offer the caller the updated slots"
    )


def test_a_provide_name_request_maps_to_a_naming_of_the_slots_still_open() -> None:
    mapper = views.MapToNamingSpec(
        request=client.ProvideNameRequest(booking_id="b-1", name="Ada"),
        available=slot_directory.AvailableSlotsResponse(slots=("mon-9am", "tue-2pm")),
    )

    assert mapper.name == "Ada"
    assert mapper.offered.labels == ("mon-9am", "tue-2pm")


def test_a_booking_that_has_not_been_named_yet_saves_a_blank_name_and_choice() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )

    mapper = views.MapToSaveBookingRequest(booking, domain.BookingID("b-1"))

    assert mapper.booking_id == "b-1"
    assert mapper.step == "collect_name"
    assert mapper.name == ""
    assert mapper.chosen == ""
    assert mapper.offered == ()


def test_a_booking_that_chose_a_slot_saves_the_name_the_choice_and_the_offer() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )
    booking.provide_name(
        domain.NamingSpec(name="Ada", offered=domain.OfferSpec(labels=("mon-9am", "tue-2pm")))
    )
    booking.choose_slot(domain.Slot("mon-9am"))

    mapper = views.MapToSaveBookingRequest(booking, domain.BookingID("b-1"))

    assert mapper.step == "confirm"
    assert mapper.name == "Ada"
    assert mapper.chosen == "mon-9am"
    assert mapper.offered == ("mon-9am", "tue-2pm")
