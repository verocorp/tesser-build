from __future__ import annotations

import pytest

import scheduling.application.ports.booking_repository as booking_repository
import scheduling.application.ports.slot_directory as slot_directory
import scheduling.application.views as views
import scheduling.domain.scheduling as domain


def test_only_returns_the_one_row_the_repository_found() -> None:
    view = booking_repository.BookingView(
        step="confirm", name="Ada", chosen="mon-9am", offered=("mon-9am",)
    )
    found = booking_repository.FindBookingResponse(
        presence=booking_repository.BookingPresence.PRESENT, bookings=(view,)
    )

    assert views.only(found) is view


def test_only_refuses_a_booking_the_repository_does_not_hold() -> None:
    found = booking_repository.FindBookingResponse(
        presence=booking_repository.BookingPresence.ABSENT, bookings=()
    )

    with pytest.raises(KeyError):
        views.only(found)


def test_loaded_rebuilds_the_booking_the_row_recorded() -> None:
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

    booking = views.loaded(found)

    assert str(booking.step()) == "confirm"
    assert str(booking.name()) == "Ada Lovelace"
    assert str(booking.chosen()) == "mon-9am"
    assert tuple(str(slot) for slot in booking.offered()) == ("mon-9am", "tue-2pm")


def test_loaded_refuses_a_booking_the_repository_does_not_hold() -> None:
    found = booking_repository.FindBookingResponse(
        presence=booking_repository.BookingPresence.ABSENT, bookings=()
    )

    with pytest.raises(KeyError):
        views.loaded(found)


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


def test_a_reserved_slot_settles_the_booking_that_was_confirmed() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="booked", name="Ada", chosen="mon-9am", offered=("mon-9am",))
    )
    view = booking_repository.BookingView(
        step="confirm", name="Ada", chosen="mon-9am", offered=("mon-9am",)
    )
    reserved = slot_directory.ReserveSlotResponse(
        outcome=slot_directory.ReservationOutcome.RESERVED, available=()
    )

    assert views.confirmed(reserved, booking, view) is booking


def test_a_taken_slot_settles_as_a_fresh_offer_from_the_stored_row() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="booked", name="Ada", chosen="mon-9am", offered=("mon-9am",))
    )
    view = booking_repository.BookingView(
        step="confirm", name="Ada", chosen="mon-9am", offered=("mon-9am",)
    )
    reserved = slot_directory.ReserveSlotResponse(
        outcome=slot_directory.ReservationOutcome.SLOT_TAKEN, available=("tue-2pm",)
    )

    settled = views.confirmed(reserved, booking, view)

    assert str(settled.step()) == "choose_slot"
    assert settled.chosen() is None
    assert tuple(str(slot) for slot in settled.offered()) == ("tue-2pm",)


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
