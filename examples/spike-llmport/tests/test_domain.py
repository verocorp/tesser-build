import pytest

from scheduling.domain import (
    Booking,
    BookingSpec,
    CustomerName,
    DomainError,
    DomainKind,
    Slot,
    Step,
)


def test_customer_name_equality() -> None:
    assert CustomerName("Ada") == CustomerName("Ada")
    assert CustomerName("Ada") != CustomerName("Bob")
    assert hash(CustomerName("Ada")) == hash(CustomerName("Ada"))


def test_slot_equality() -> None:
    assert Slot("mon-9am") == Slot("mon-9am")
    assert Slot("mon-9am") != Slot("tue-2pm")
    assert hash(Slot("mon-9am")) == hash(Slot("mon-9am"))


def test_empty_name_is_rejected() -> None:
    with pytest.raises(DomainError) as excinfo:
        CustomerName("   ")
    assert excinfo.value.kind is DomainKind.VALIDATION


def test_the_booking_walks_its_steps() -> None:
    booking = Booking(BookingSpec())
    assert booking.step() is Step.COLLECT_NAME

    booking.provide_name(CustomerName("Ada"), (Slot("mon-9am"), Slot("tue-2pm")))
    assert booking.step() is Step.CHOOSE_SLOT

    booking.choose_slot(Slot("mon-9am"))
    assert booking.step() is Step.CONFIRM
    assert booking.chosen_slot() == Slot("mon-9am")

    booking.confirm()
    assert booking.step() is Step.BOOKED


def test_an_unoffered_slot_is_rejected_naming_the_offered() -> None:
    booking = Booking(BookingSpec())
    booking.provide_name(CustomerName("Ada"), (Slot("mon-9am"), Slot("tue-2pm")))

    with pytest.raises(DomainError) as excinfo:
        booking.choose_slot(Slot("wed-4pm"))

    assert excinfo.value.kind is DomainKind.VALIDATION
    assert "mon-9am" in excinfo.value.message
    assert "tue-2pm" in excinfo.value.message
    assert booking.step() is Step.CHOOSE_SLOT


def test_rechoosing_at_confirm_overwrites_the_choice() -> None:
    booking = Booking(BookingSpec())
    booking.provide_name(CustomerName("Ada"), (Slot("mon-9am"), Slot("tue-2pm")))
    booking.choose_slot(Slot("mon-9am"))

    booking.choose_slot(Slot("tue-2pm"))

    assert booking.step() is Step.CONFIRM
    assert booking.chosen_slot() == Slot("tue-2pm")


def test_a_step_out_of_order_is_a_validation_error() -> None:
    booking = Booking(BookingSpec())

    with pytest.raises(DomainError) as excinfo:
        booking.confirm()

    assert excinfo.value.kind is DomainKind.VALIDATION
    assert excinfo.value.code == "wrong_step"


def test_reoffer_replaces_slots_and_returns_to_choosing() -> None:
    booking = Booking(BookingSpec())
    booking.provide_name(CustomerName("Ada"), (Slot("mon-9am"),))
    booking.choose_slot(Slot("mon-9am"))

    booking.reoffer((Slot("tue-2pm"),))

    assert booking.step() is Step.CHOOSE_SLOT
    assert booking.offered_slots() == (Slot("tue-2pm"),)
    with pytest.raises(DomainError):
        booking.chosen_slot()
