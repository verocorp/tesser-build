import pytest
import tesser.testing as ts

import scheduling.application as application
import scheduling.client as client


@ts.fake
class MemorySlotDirectory(application.SlotDirectory):

    def __init__(self, slots: tuple[str, ...]) -> None:
        self.slots = list(slots)
        self.reserved: list[tuple[str, str]] = []

    def available(self) -> tuple[str, ...]:
        return tuple(self.slots)

    def reserve(self, slot: str, name: str) -> None:
        if slot not in self.slots:
            raise ValueError(f"slot {slot} was just taken")
        self.slots.remove(slot)
        self.reserved.append((slot, name))


@ts.fake
class MemoryBookingRepository(application.BookingRepository):

    def __init__(self) -> None:
        self.stored: dict[str, application.BookingParts] = {}

    def has(self, booking_id: str) -> bool:
        return booking_id in self.stored

    def get(self, booking_id: str) -> application.BookingParts:
        return self.stored[booking_id]

    def save(self, booking_id: str, parts: application.BookingParts) -> None:
        self.stored[booking_id] = parts


@ts.fake
class DownSlotDirectory(application.SlotDirectory):

    def available(self) -> tuple[str, ...]:
        raise RuntimeError("slot directory unreachable")

    def reserve(self, slot: str, name: str) -> None:
        raise RuntimeError("slot directory unreachable")


def test_the_full_booking_flow_through_the_client_surface() -> None:
    directory = MemorySlotDirectory(("mon-9am", "tue-2pm"))
    repository = MemoryBookingRepository()
    service = application.BookingService(directory, repository)

    state = service.begin(client.BeginBookingRequest(booking_id="b1"))
    assert isinstance(state, client.BookingStateResponse)
    assert state.step == "collect_name"

    state = service.provide_name(
        client.ProvideNameRequest(booking_id="b1", name="Ada Lovelace")
    )
    assert state.step == "choose_slot"
    assert state.offered_slots == ("mon-9am", "tue-2pm")

    state = service.choose_slot(client.ChooseSlotRequest(booking_id="b1", slot="mon-9am"))
    assert state.step == "confirm"

    state = service.confirm(client.ConfirmBookingRequest(booking_id="b1"))
    assert state.step == "booked"
    assert "mon-9am" in state.reply
    assert directory.reserved == [("mon-9am", "Ada Lovelace")]
    assert repository.stored["b1"].step == "booked"
    assert repository.stored["b1"].name == "Ada Lovelace"
    assert repository.stored["b1"].chosen == "mon-9am"


def test_a_rejected_transition_persists_nothing() -> None:
    directory = MemorySlotDirectory(("mon-9am",))
    repository = MemoryBookingRepository()
    service = application.BookingService(directory, repository)
    service.begin(client.BeginBookingRequest(booking_id="b1"))
    service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))

    with pytest.raises(ValueError):
        service.choose_slot(client.ChooseSlotRequest(booking_id="b1", slot="wed-4pm"))

    assert repository.stored["b1"].step == "choose_slot"
    assert repository.stored["b1"].chosen == ""


def test_a_slot_taken_between_choice_and_confirm_surfaces_and_reoffer_recovers() -> None:
    directory = MemorySlotDirectory(("mon-9am", "tue-2pm"))
    repository = MemoryBookingRepository()
    service = application.BookingService(directory, repository)
    service.begin(client.BeginBookingRequest(booking_id="b1"))
    service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))
    service.choose_slot(client.ChooseSlotRequest(booking_id="b1", slot="mon-9am"))

    directory.slots.remove("mon-9am")
    with pytest.raises(ValueError) as excinfo:
        service.confirm(client.ConfirmBookingRequest(booking_id="b1"))

    assert "taken" in str(excinfo.value)
    assert repository.stored["b1"].step == "confirm"

    state = service.reoffer(client.ReofferRequest(booking_id="b1"))
    assert state.step == "choose_slot"
    assert state.offered_slots == ("tue-2pm",)

    service.choose_slot(client.ChooseSlotRequest(booking_id="b1", slot="tue-2pm"))
    state = service.confirm(client.ConfirmBookingRequest(booking_id="b1"))
    assert state.step == "booked"


def test_status_reads_without_mutating() -> None:
    directory = MemorySlotDirectory(("mon-9am",))
    repository = MemoryBookingRepository()
    service = application.BookingService(directory, repository)
    service.begin(client.BeginBookingRequest(booking_id="b1"))
    service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))

    state = service.status(client.StatusRequest(booking_id="b1"))

    assert state.step == "choose_slot"
    assert state.offered_slots == ("mon-9am",)
    assert repository.stored["b1"].step == "choose_slot"


def test_an_infrastructure_failure_passes_through_untranslated() -> None:
    service = application.BookingService(DownSlotDirectory(), MemoryBookingRepository())
    service.begin(client.BeginBookingRequest(booking_id="b1"))

    with pytest.raises(RuntimeError):
        service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))


def test_begin_resumes_an_in_flight_booking() -> None:
    directory = MemorySlotDirectory(("mon-9am",))
    repository = MemoryBookingRepository()
    service = application.BookingService(directory, repository)
    service.begin(client.BeginBookingRequest(booking_id="b1"))
    service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))

    state = service.begin(client.BeginBookingRequest(booking_id="b1"))

    assert state.step == "choose_slot"
    assert state.offered_slots == ("mon-9am",)
    assert state.reply == "continue the booking"
    assert repository.stored["b1"].name == "Ada"


def test_begin_resumes_a_booked_booking_without_touching_it() -> None:
    directory = MemorySlotDirectory(("mon-9am",))
    repository = MemoryBookingRepository()
    service = application.BookingService(directory, repository)
    service.begin(client.BeginBookingRequest(booking_id="b1"))
    service.provide_name(client.ProvideNameRequest(booking_id="b1", name="Ada"))
    service.choose_slot(client.ChooseSlotRequest(booking_id="b1", slot="mon-9am"))
    service.confirm(client.ConfirmBookingRequest(booking_id="b1"))

    state = service.begin(client.BeginBookingRequest(booking_id="b1"))

    assert state.step == "booked"
    assert repository.stored["b1"].step == "booked"
    assert directory.reserved == [("mon-9am", "Ada")]


def test_an_unknown_booking_id_is_not_a_domain_rejection() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )

    with pytest.raises(KeyError):
        service.status(client.StatusRequest(booking_id="ghost"))
