import pytest

import scheduling.domain as domain


def test_customer_name_equality() -> None:
    assert domain.CustomerName("Ada") == domain.CustomerName("Ada")
    assert domain.CustomerName("Ada") != domain.CustomerName("Bob")
    assert hash(domain.CustomerName("Ada")) == hash(domain.CustomerName("Ada"))


def test_slot_equality() -> None:
    assert domain.Slot("mon-9am") == domain.Slot("mon-9am")
    assert domain.Slot("mon-9am") != domain.Slot("tue-2pm")
    assert hash(domain.Slot("mon-9am")) == hash(domain.Slot("mon-9am"))


def test_step_equality() -> None:
    assert domain.Step("confirm") == domain.Step("confirm")
    assert domain.Step("confirm") != domain.Step("booked")
    assert hash(domain.Step("confirm")) == hash(domain.Step("confirm"))


def test_names_and_slots_normalize_surrounding_whitespace() -> None:
    assert domain.CustomerName("  Ada  ") == domain.CustomerName("Ada")
    assert str(domain.CustomerName("  Ada  ")) == "Ada"
    assert domain.Slot("  mon-9am ") == domain.Slot("mon-9am")
    assert str(domain.Slot("  mon-9am ")) == "mon-9am"


def test_empty_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        domain.CustomerName("   ")


def test_a_whitespace_slot_label_is_rejected() -> None:
    with pytest.raises(ValueError):
        domain.Slot("   ")


def test_oversized_names_and_slot_labels_are_rejected() -> None:
    with pytest.raises(ValueError):
        domain.CustomerName("a" * 201)
    with pytest.raises(ValueError):
        domain.Slot("s" * 101)
    assert str(domain.CustomerName("a" * 200)) == "a" * 200


def test_a_step_outside_the_closed_set_is_rejected() -> None:
    with pytest.raises(ValueError):
        domain.Step("shipped")


def test_the_booking_walks_its_steps() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )
    assert booking.step_label() == "collect_name"

    booking.provide_name(
        domain.CustomerName("Ada"), (domain.Slot("mon-9am"), domain.Slot("tue-2pm"))
    )
    assert booking.step_label() == "choose_slot"

    booking.choose_slot(domain.Slot("mon-9am"))
    assert booking.step_label() == "confirm"
    assert booking.slot_label() == "mon-9am"

    booking.confirm()
    assert booking.step_label() == "booked"


def test_the_booking_reconstructs_from_its_parts() -> None:
    spec = domain.BookingSpec(
        step="confirm", name="Ada", chosen="mon-9am", offered=("mon-9am", "tue-2pm")
    )
    booking = domain.Booking(spec)

    assert booking.step_label() == "confirm"
    assert booking.name_label() == "Ada"
    assert booking.slot_label() == "mon-9am"
    assert booking.offered_labels() == ("mon-9am", "tue-2pm")


def test_an_unoffered_slot_is_rejected_naming_the_offered() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )
    booking.provide_name(
        domain.CustomerName("Ada"), (domain.Slot("mon-9am"), domain.Slot("tue-2pm"))
    )

    with pytest.raises(ValueError) as excinfo:
        booking.choose_slot(domain.Slot("wed-4pm"))

    assert "mon-9am" in str(excinfo.value)
    assert "tue-2pm" in str(excinfo.value)
    assert booking.step_label() == "choose_slot"


def test_rechoosing_at_confirm_overwrites_the_choice() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )
    booking.provide_name(
        domain.CustomerName("Ada"), (domain.Slot("mon-9am"), domain.Slot("tue-2pm"))
    )
    booking.choose_slot(domain.Slot("mon-9am"))

    booking.choose_slot(domain.Slot("tue-2pm"))

    assert booking.step_label() == "confirm"
    assert booking.slot_label() == "tue-2pm"


def test_a_step_out_of_order_is_rejected() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )

    with pytest.raises(ValueError) as excinfo:
        booking.confirm()

    assert "collect_name" in str(excinfo.value)


def test_reoffer_replaces_slots_and_returns_to_choosing() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )
    booking.provide_name(domain.CustomerName("Ada"), (domain.Slot("mon-9am"),))
    booking.choose_slot(domain.Slot("mon-9am"))

    booking.reoffer((domain.Slot("tue-2pm"),))

    assert booking.step_label() == "choose_slot"
    assert booking.offered_labels() == ("tue-2pm",)
    assert booking.slot_label() == ""


def test_every_step_constant_constructs() -> None:
    for label in domain.STEPS:
        assert str(domain.Step(label)) == label


def test_provide_name_with_no_slots_available_is_rejected() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )

    with pytest.raises(ValueError) as excinfo:
        booking.provide_name(domain.CustomerName("Ada"), ())

    assert "no slots are available" in str(excinfo.value)
    assert booking.step_label() == "collect_name"


def test_reoffer_with_no_slots_available_is_rejected() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )
    booking.provide_name(domain.CustomerName("Ada"), (domain.Slot("mon-9am"),))
    booking.choose_slot(domain.Slot("mon-9am"))

    with pytest.raises(ValueError) as excinfo:
        booking.reoffer(())

    assert "no slots are available" in str(excinfo.value)
    assert booking.step_label() == "confirm"


def test_choosing_before_any_offer_or_after_booking_is_rejected() -> None:
    fresh = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )
    with pytest.raises(ValueError) as excinfo:
        fresh.choose_slot(domain.Slot("mon-9am"))
    assert "collect_name" in str(excinfo.value)

    booked = domain.Booking(
        domain.BookingSpec(step="booked", name="Ada", chosen="mon-9am", offered=("mon-9am",))
    )
    with pytest.raises(ValueError) as excinfo:
        booked.choose_slot(domain.Slot("mon-9am"))
    assert "booked" in str(excinfo.value)


def test_reconstitution_rejects_inconsistent_parts() -> None:
    with pytest.raises(ValueError):
        domain.Booking(domain.BookingSpec(step="confirm", name="", chosen="", offered=()))
    with pytest.raises(ValueError):
        domain.Booking(domain.BookingSpec(step="confirm", name="Ada", chosen="", offered=("mon-9am",)))
    with pytest.raises(ValueError):
        domain.Booking(domain.BookingSpec(step="booked", name="", chosen="", offered=()))
    with pytest.raises(ValueError):
        domain.Booking(domain.BookingSpec(step="choose_slot", name="Ada", chosen="", offered=()))
    with pytest.raises(ValueError):
        domain.Booking(domain.BookingSpec(step="collect_name", name="Ada", chosen="", offered=()))
    with pytest.raises(ValueError):
        domain.Booking(domain.BookingSpec(step="confirm", name="Ada", chosen="wed-4pm", offered=("mon-9am",)))
