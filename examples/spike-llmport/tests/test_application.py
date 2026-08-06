import pytest

from scheduling.application import BookingService
from scheduling.client import (
    BeginBookingRequest,
    BookingStateResponse,
    ChooseSlotRequest,
    ConfirmBookingRequest,
    ProvideNameRequest,
    ReofferRequest,
    StatusRequest,
)
from tests.fakes import DownSlotDirectory, MemoryBookingRepository, MemorySlotDirectory


def test_the_full_booking_flow_through_the_client_surface() -> None:
    directory = MemorySlotDirectory(("mon-9am", "tue-2pm"))
    repository = MemoryBookingRepository()
    service = BookingService(directory, repository)

    state = service.begin(BeginBookingRequest(booking_id="b1"))
    assert isinstance(state, BookingStateResponse)
    assert state.step == "collect_name"

    state = service.provide_name(ProvideNameRequest(booking_id="b1", name="Ada Lovelace"))
    assert state.step == "choose_slot"
    assert state.offered_slots == ("mon-9am", "tue-2pm")

    state = service.choose_slot(ChooseSlotRequest(booking_id="b1", slot="mon-9am"))
    assert state.step == "confirm"

    state = service.confirm(ConfirmBookingRequest(booking_id="b1"))
    assert state.step == "booked"
    assert "mon-9am" in state.reply
    assert directory.reserved == [("mon-9am", "Ada Lovelace")]
    assert repository.stored["b1"].step == "booked"
    assert repository.stored["b1"].name == "Ada Lovelace"
    assert repository.stored["b1"].chosen == "mon-9am"


def test_a_rejected_transition_persists_nothing() -> None:
    directory = MemorySlotDirectory(("mon-9am",))
    repository = MemoryBookingRepository()
    service = BookingService(directory, repository)
    service.begin(BeginBookingRequest(booking_id="b1"))
    service.provide_name(ProvideNameRequest(booking_id="b1", name="Ada"))

    with pytest.raises(ValueError):
        service.choose_slot(ChooseSlotRequest(booking_id="b1", slot="wed-4pm"))

    assert repository.stored["b1"].step == "choose_slot"
    assert repository.stored["b1"].chosen == ""


def test_a_slot_taken_between_choice_and_confirm_surfaces_and_reoffer_recovers() -> None:
    directory = MemorySlotDirectory(("mon-9am", "tue-2pm"))
    repository = MemoryBookingRepository()
    service = BookingService(directory, repository)
    service.begin(BeginBookingRequest(booking_id="b1"))
    service.provide_name(ProvideNameRequest(booking_id="b1", name="Ada"))
    service.choose_slot(ChooseSlotRequest(booking_id="b1", slot="mon-9am"))

    directory.slots.remove("mon-9am")
    with pytest.raises(ValueError) as excinfo:
        service.confirm(ConfirmBookingRequest(booking_id="b1"))

    assert "taken" in str(excinfo.value)
    assert repository.stored["b1"].step == "confirm"

    state = service.reoffer(ReofferRequest(booking_id="b1"))
    assert state.step == "choose_slot"
    assert state.offered_slots == ("tue-2pm",)

    service.choose_slot(ChooseSlotRequest(booking_id="b1", slot="tue-2pm"))
    state = service.confirm(ConfirmBookingRequest(booking_id="b1"))
    assert state.step == "booked"


def test_status_reads_without_mutating() -> None:
    directory = MemorySlotDirectory(("mon-9am",))
    repository = MemoryBookingRepository()
    service = BookingService(directory, repository)
    service.begin(BeginBookingRequest(booking_id="b1"))
    service.provide_name(ProvideNameRequest(booking_id="b1", name="Ada"))

    state = service.status(StatusRequest(booking_id="b1"))

    assert state.step == "choose_slot"
    assert state.offered_slots == ("mon-9am",)
    assert repository.stored["b1"].step == "choose_slot"


def test_an_infrastructure_failure_passes_through_untranslated() -> None:
    service = BookingService(DownSlotDirectory(), MemoryBookingRepository())
    service.begin(BeginBookingRequest(booking_id="b1"))

    with pytest.raises(RuntimeError):
        service.provide_name(ProvideNameRequest(booking_id="b1", name="Ada"))
