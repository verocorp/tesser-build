import pytest

import scheduling.domain.scheduling as domain


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
    assert str(booking.step()) == "collect_name"

    booking.provide_name(
        domain.NamingSpec(
            name="Ada", offered=domain.OfferSpec(labels=("mon-9am", "tue-2pm"))
        )
    )
    assert str(booking.step()) == "choose_slot"

    booking.choose_slot(domain.Slot("mon-9am"))
    assert str(booking.step()) == "confirm"
    assert str(booking.chosen()) == "mon-9am"

    booking.confirm()
    assert str(booking.step()) == "booked"


def test_the_booking_reconstructs_from_its_parts() -> None:
    spec = domain.BookingSpec(
        step="confirm", name="Ada", chosen="mon-9am", offered=("mon-9am", "tue-2pm")
    )
    booking = domain.Booking(spec)

    assert str(booking.step()) == "confirm"
    assert str(booking.name()) == "Ada"
    assert str(booking.chosen()) == "mon-9am"
    assert tuple(str(s) for s in booking.offered()) == ("mon-9am", "tue-2pm")


def test_an_unoffered_slot_is_rejected_naming_the_offered() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )
    booking.provide_name(
        domain.NamingSpec(
            name="Ada", offered=domain.OfferSpec(labels=("mon-9am", "tue-2pm"))
        )
    )

    with pytest.raises(ValueError) as excinfo:
        booking.choose_slot(domain.Slot("wed-4pm"))

    assert "mon-9am" in str(excinfo.value)
    assert "tue-2pm" in str(excinfo.value)
    assert str(booking.step()) == "choose_slot"


def test_rechoosing_at_confirm_overwrites_the_choice() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )
    booking.provide_name(
        domain.NamingSpec(
            name="Ada", offered=domain.OfferSpec(labels=("mon-9am", "tue-2pm"))
        )
    )
    booking.choose_slot(domain.Slot("mon-9am"))

    booking.choose_slot(domain.Slot("tue-2pm"))

    assert str(booking.step()) == "confirm"
    assert str(booking.chosen()) == "tue-2pm"


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
    booking.provide_name(
        domain.NamingSpec(name="Ada", offered=domain.OfferSpec(labels=("mon-9am",)))
    )
    booking.choose_slot(domain.Slot("mon-9am"))

    booking.reoffer(domain.OfferSpec(labels=("tue-2pm",)))

    assert str(booking.step()) == "choose_slot"
    assert tuple(str(s) for s in booking.offered()) == ("tue-2pm",)
    assert booking.chosen() is None


def test_every_step_constant_constructs() -> None:
    for label in domain.STEPS:
        assert str(domain.Step(label)) == label


def test_provide_name_with_no_slots_available_is_rejected() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )

    with pytest.raises(ValueError) as excinfo:
        booking.provide_name(
            domain.NamingSpec(name="Ada", offered=domain.OfferSpec(labels=()))
        )

    assert "no slots are available" in str(excinfo.value)
    assert str(booking.step()) == "collect_name"


def test_reoffer_with_no_slots_available_is_rejected() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )
    booking.provide_name(
        domain.NamingSpec(name="Ada", offered=domain.OfferSpec(labels=("mon-9am",)))
    )
    booking.choose_slot(domain.Slot("mon-9am"))

    with pytest.raises(ValueError) as excinfo:
        booking.reoffer(domain.OfferSpec(labels=()))

    assert "no slots are available" in str(excinfo.value)
    assert str(booking.step()) == "confirm"


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


def test_booking_id_equality() -> None:
    assert domain.BookingID("b1") == domain.BookingID("b1")
    assert domain.BookingID("b1") != domain.BookingID("b2")
    assert hash(domain.BookingID("b1")) == hash(domain.BookingID("b1"))


def test_a_booking_id_must_be_non_empty() -> None:
    with pytest.raises(ValueError, match="booking id must be non-empty"):
        domain.BookingID("")


def test_a_booking_id_is_kept_exactly_as_it_was_given() -> None:
    assert str(domain.BookingID(" b1 ")) == " b1 "


def test_settling_with_no_reoffer_leaves_the_booking_booked() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="booked", name="Ada", chosen="mon-9am", offered=("mon-9am",))
    )

    settled = booking.settle(domain.Reoffers(domain.ReoffersSpec(offered=())))

    assert settled is domain.Settled.BOOKED
    assert str(booking.step()) == "booked"
    assert str(booking.chosen()) == "mon-9am"


def test_settling_with_a_reoffer_sends_the_booking_back_to_choosing() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="booked", name="Ada", chosen="mon-9am", offered=("mon-9am",))
    )

    settled = booking.settle(domain.Reoffers(domain.ReoffersSpec(offered=(("tue-2pm",),))))

    assert settled is domain.Settled.REOFFERED
    assert str(booking.step()) == "choose_slot"
    assert booking.chosen() is None
    assert tuple(str(slot) for slot in booking.offered()) == ("tue-2pm",)


def test_settling_with_an_empty_reoffer_is_an_error() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="booked", name="Ada", chosen="mon-9am", offered=("mon-9am",))
    )

    with pytest.raises(ValueError, match="no slots are available"):
        booking.settle(domain.Reoffers(domain.ReoffersSpec(offered=((),))))


def test_settling_a_booking_that_was_never_booked_is_an_error() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="confirm", name="Ada", chosen="mon-9am", offered=("mon-9am",))
    )

    with pytest.raises(ValueError, match="not available at step"):
        booking.settle(domain.Reoffers(domain.ReoffersSpec(offered=())))


def test_reoffers_turn_every_offered_label_into_a_slot() -> None:
    reoffers = domain.Reoffers(domain.ReoffersSpec(offered=(("mon-9am", "tue-2pm"),)))

    assert tuple(
        tuple(str(slot) for slot in each) for each in reoffers.offered
    ) == (("mon-9am", "tue-2pm"),)


def test_reoffers_refuse_a_slot_label_that_is_blank() -> None:
    with pytest.raises(ValueError, match="slot label must be non-empty"):
        domain.Reoffers(domain.ReoffersSpec(offered=((" ",),)))


def test_reoffers_are_equal_when_they_offer_the_same_slots() -> None:
    one = domain.Reoffers(domain.ReoffersSpec(offered=(("mon-9am",),)))
    same = domain.Reoffers(domain.ReoffersSpec(offered=(("mon-9am",),)))
    other = domain.Reoffers(domain.ReoffersSpec(offered=(("tue-2pm",),)))

    assert one == same
    assert one != other
    assert len({one, same, other}) == 2


def test_an_offer_turns_every_label_into_a_slot() -> None:
    offer = domain.Offer(domain.OfferSpec(labels=("mon-9am", "tue-2pm")))

    assert tuple(str(slot) for slot in offer.slots) == ("mon-9am", "tue-2pm")


def test_an_offer_of_nothing_is_rejected() -> None:
    with pytest.raises(ValueError) as excinfo:
        domain.Offer(domain.OfferSpec(labels=()))

    assert "no slots are available" in str(excinfo.value)


def test_an_offer_is_equal_when_it_offers_the_same_slots() -> None:
    one = domain.Offer(domain.OfferSpec(labels=("mon-9am",)))
    same = domain.Offer(domain.OfferSpec(labels=("mon-9am",)))
    other = domain.Offer(domain.OfferSpec(labels=("tue-2pm",)))

    assert one == same
    assert one != other


def test_a_naming_carries_the_name_and_the_offer_it_was_built_from() -> None:
    naming = domain.Naming(
        domain.NamingSpec(name="Ada", offered=domain.OfferSpec(labels=("mon-9am",)))
    )

    assert str(naming.name) == "Ada"
    assert tuple(str(slot) for slot in naming.offer.slots) == ("mon-9am",)


def test_a_naming_with_a_blank_name_is_rejected() -> None:
    with pytest.raises(ValueError):
        domain.Naming(
            domain.NamingSpec(name="  ", offered=domain.OfferSpec(labels=("mon-9am",)))
        )


def test_naming_a_booking_that_is_past_collecting_a_name_is_rejected() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="confirm", name="Ada", chosen="mon-9am", offered=("mon-9am",))
    )

    with pytest.raises(ValueError, match="not available at step"):
        booking.provide_name(
            domain.NamingSpec(name="Grace", offered=domain.OfferSpec(labels=("tue-2pm",)))
        )

    assert str(booking.step()) == "confirm"


def test_reoffering_before_a_slot_was_chosen_is_rejected() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )

    with pytest.raises(ValueError, match="not available at step"):
        booking.reoffer(domain.OfferSpec(labels=("mon-9am",)))

    assert str(booking.step()) == "collect_name"


def test_a_wrong_step_is_reported_before_the_offer_is_read() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="confirm", name="Ada", chosen="mon-9am", offered=("mon-9am",))
    )

    with pytest.raises(ValueError, match="not available at step"):
        booking.provide_name(
            domain.NamingSpec(name="Grace", offered=domain.OfferSpec(labels=()))
        )

    assert str(booking.step()) == "confirm"


def test_an_offer_of_nothing_is_refused_at_the_step_that_reads_it() -> None:
    booking = domain.Booking(
        domain.BookingSpec(step="collect_name", name="", chosen="", offered=())
    )

    with pytest.raises(ValueError, match="no slots are available"):
        booking.provide_name(
            domain.NamingSpec(name="Grace", offered=domain.OfferSpec(labels=()))
        )

    assert str(booking.step()) == "collect_name"


def test_a_naming_is_equal_when_it_names_the_same_customer_and_offer() -> None:
    one = domain.Naming(
        domain.NamingSpec(name="Ada", offered=domain.OfferSpec(labels=("mon-9am",)))
    )
    same = domain.Naming(
        domain.NamingSpec(name="Ada", offered=domain.OfferSpec(labels=("mon-9am",)))
    )
    other = domain.Naming(
        domain.NamingSpec(name="Grace", offered=domain.OfferSpec(labels=("mon-9am",)))
    )

    assert one == same
    assert one != other


def test_a_stored_booking_resumes() -> None:
    resumption = domain.Resumption(domain.ResumptionSpec(presence="present"))

    assert resumption.resumed() is domain.Resumed.RESUMED


def test_a_booking_the_repository_does_not_hold_starts() -> None:
    resumption = domain.Resumption(domain.ResumptionSpec(presence="absent"))

    assert resumption.resumed() is domain.Resumed.STARTED


def test_a_presence_outside_the_closed_set_is_rejected() -> None:
    with pytest.raises(ValueError, match="is not a presence"):
        domain.Resumption(domain.ResumptionSpec(presence="maybe"))


def test_resumption_equality() -> None:
    assert domain.Resumption(domain.ResumptionSpec(presence="present")) == domain.Resumption(
        domain.ResumptionSpec(presence="present")
    )
    assert domain.Resumption(domain.ResumptionSpec(presence="present")) != domain.Resumption(
        domain.ResumptionSpec(presence="absent")
    )
