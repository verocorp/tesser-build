from __future__ import annotations

import scheduling.adapters.repositories as repositories
import scheduling.application.ports as ports


def test_an_unknown_booking_comes_back_absent_and_empty() -> None:
    memory_booking_repository = repositories.MemoryBookingRepository()

    find_booking_response = memory_booking_repository.find(
        ports.FindBookingRequest(booking_id="ghost")
    )

    assert find_booking_response.presence is ports.BookingPresence.ABSENT
    assert find_booking_response.bookings == ()


def test_a_saved_booking_comes_back_present_with_every_field() -> None:
    memory_booking_repository = repositories.MemoryBookingRepository()
    memory_booking_repository.save(
        ports.SaveBookingRequest(
            booking_id="b1",
            step="confirm",
            name="Ada Lovelace",
            chosen="mon-9am",
            offered=("mon-9am", "tue-2pm"),
        )
    )

    find_booking_response = memory_booking_repository.find(
        ports.FindBookingRequest(booking_id="b1")
    )

    assert find_booking_response.presence is ports.BookingPresence.PRESENT
    assert len(find_booking_response.bookings) == 1
    view = find_booking_response.bookings[0]
    assert view.step == "confirm"
    assert view.name == "Ada Lovelace"
    assert view.chosen == "mon-9am"
    assert view.offered == ("mon-9am", "tue-2pm")


def test_saving_the_same_booking_again_replaces_what_was_there() -> None:
    memory_booking_repository = repositories.MemoryBookingRepository()
    memory_booking_repository.save(
        ports.SaveBookingRequest(
            booking_id="b1", step="choose_slot", name="Ada", chosen="", offered=("mon-9am",)
        )
    )

    memory_booking_repository.save(
        ports.SaveBookingRequest(
            booking_id="b1", step="confirm", name="Ada", chosen="mon-9am", offered=("mon-9am",)
        )
    )

    view = memory_booking_repository.find(
        ports.FindBookingRequest(booking_id="b1")
    ).bookings[0]
    assert view.step == "confirm"
    assert view.chosen == "mon-9am"


def test_two_bookings_are_stored_apart() -> None:
    memory_booking_repository = repositories.MemoryBookingRepository()
    memory_booking_repository.save(
        ports.SaveBookingRequest(
            booking_id="b1", step="collect_name", name="", chosen="", offered=()
        )
    )
    memory_booking_repository.save(
        ports.SaveBookingRequest(
            booking_id="b2", step="booked", name="Grace", chosen="tue-2pm", offered=("tue-2pm",)
        )
    )

    first = memory_booking_repository.find(
        ports.FindBookingRequest(booking_id="b1")
    ).bookings[0]
    second = memory_booking_repository.find(
        ports.FindBookingRequest(booking_id="b2")
    ).bookings[0]

    assert first.step == "collect_name"
    assert second.step == "booked"
    assert second.name == "Grace"


def test_a_booking_with_nothing_recorded_yet_round_trips_as_empty_fields() -> None:
    memory_booking_repository = repositories.MemoryBookingRepository()
    memory_booking_repository.save(
        ports.SaveBookingRequest(
            booking_id="b1", step="collect_name", name="", chosen="", offered=()
        )
    )

    view = memory_booking_repository.find(
        ports.FindBookingRequest(booking_id="b1")
    ).bookings[0]

    assert view.name == ""
    assert view.chosen == ""
    assert view.offered == ()


def test_finding_a_booking_leaves_it_in_place() -> None:
    memory_booking_repository = repositories.MemoryBookingRepository()
    memory_booking_repository.save(
        ports.SaveBookingRequest(
            booking_id="b1", step="booked", name="Ada", chosen="mon-9am", offered=("mon-9am",)
        )
    )

    memory_booking_repository.find(ports.FindBookingRequest(booking_id="b1"))
    find_booking_response = memory_booking_repository.find(
        ports.FindBookingRequest(booking_id="b1")
    )

    assert find_booking_response.presence is ports.BookingPresence.PRESENT
    assert find_booking_response.bookings[0].step == "booked"
