from __future__ import annotations

import scheduling.adapters.repositories.repo_memory as repo_memory
import scheduling.application.ports.booking_repository as booking_repository


def test_an_unknown_booking_comes_back_absent_and_empty() -> None:
    repository = repo_memory.MemoryBookingRepository()

    found = repository.find(booking_repository.FindBookingRequest(booking_id="ghost"))

    assert found.presence is booking_repository.BookingPresence.ABSENT
    assert found.bookings == ()


def test_a_saved_booking_comes_back_present_with_every_field() -> None:
    repository = repo_memory.MemoryBookingRepository()
    repository.save(
        booking_repository.SaveBookingRequest(
            booking_id="b1",
            step="confirm",
            name="Ada Lovelace",
            chosen="mon-9am",
            offered=("mon-9am", "tue-2pm"),
        )
    )

    found = repository.find(booking_repository.FindBookingRequest(booking_id="b1"))

    assert found.presence is booking_repository.BookingPresence.PRESENT
    assert len(found.bookings) == 1
    view = found.bookings[0]
    assert view.step == "confirm"
    assert view.name == "Ada Lovelace"
    assert view.chosen == "mon-9am"
    assert view.offered == ("mon-9am", "tue-2pm")


def test_saving_the_same_booking_again_replaces_what_was_there() -> None:
    repository = repo_memory.MemoryBookingRepository()
    repository.save(
        booking_repository.SaveBookingRequest(
            booking_id="b1", step="choose_slot", name="Ada", chosen="", offered=("mon-9am",)
        )
    )

    repository.save(
        booking_repository.SaveBookingRequest(
            booking_id="b1", step="confirm", name="Ada", chosen="mon-9am", offered=("mon-9am",)
        )
    )

    view = repository.find(booking_repository.FindBookingRequest(booking_id="b1")).bookings[0]
    assert view.step == "confirm"
    assert view.chosen == "mon-9am"


def test_two_bookings_are_stored_apart() -> None:
    repository = repo_memory.MemoryBookingRepository()
    repository.save(
        booking_repository.SaveBookingRequest(
            booking_id="b1", step="collect_name", name="", chosen="", offered=()
        )
    )
    repository.save(
        booking_repository.SaveBookingRequest(
            booking_id="b2", step="booked", name="Grace", chosen="tue-2pm", offered=("tue-2pm",)
        )
    )

    first = repository.find(booking_repository.FindBookingRequest(booking_id="b1")).bookings[0]
    second = repository.find(booking_repository.FindBookingRequest(booking_id="b2")).bookings[0]

    assert first.step == "collect_name"
    assert second.step == "booked"
    assert second.name == "Grace"


def test_a_booking_with_nothing_recorded_yet_round_trips_as_empty_fields() -> None:
    repository = repo_memory.MemoryBookingRepository()
    repository.save(
        booking_repository.SaveBookingRequest(
            booking_id="b1", step="collect_name", name="", chosen="", offered=()
        )
    )

    view = repository.find(booking_repository.FindBookingRequest(booking_id="b1")).bookings[0]

    assert view.name == ""
    assert view.chosen == ""
    assert view.offered == ()


def test_finding_a_booking_leaves_it_in_place() -> None:
    repository = repo_memory.MemoryBookingRepository()
    repository.save(
        booking_repository.SaveBookingRequest(
            booking_id="b1", step="booked", name="Ada", chosen="mon-9am", offered=("mon-9am",)
        )
    )

    repository.find(booking_repository.FindBookingRequest(booking_id="b1"))
    again = repository.find(booking_repository.FindBookingRequest(booking_id="b1"))

    assert again.presence is booking_repository.BookingPresence.PRESENT
    assert again.bookings[0].step == "booked"
