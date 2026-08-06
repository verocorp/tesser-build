import pytest

from scheduling.application import BookingService
from scheduling.domain import (
    CustomerName,
    DomainError,
    DomainKind,
    InfraError,
    Slot,
    Step,
)
from scheduling.tools import ToolName
from tests.fakes import DownSlotDirectory, MemoryBookingRepository, MemorySlotDirectory


def test_the_full_booking_flow_through_the_tool_surface() -> None:
    directory = MemorySlotDirectory((Slot("mon-9am"), Slot("tue-2pm")))
    repository = MemoryBookingRepository()
    service = BookingService(directory, repository)
    booking = service.begin()

    assert set(service.llm_tools(booking)) == {ToolName.PROVIDE_NAME}

    reply = service.execute(booking, ToolName.PROVIDE_NAME, {"name": "Ada Lovelace"})
    assert "mon-9am" in reply
    assert set(service.llm_tools(booking)) == {ToolName.CHOOSE_SLOT}

    service.execute(booking, ToolName.CHOOSE_SLOT, {"slot": "mon-9am"})
    assert ToolName.CONFIRM_BOOKING in service.llm_tools(booking)

    reply = service.execute(booking, ToolName.CONFIRM_BOOKING, {})
    assert "booked" in reply
    assert booking.step() is Step.BOOKED
    assert service.llm_tools(booking) == {}
    assert len(repository.saved) == 1
    assert repository.saved[0].name == "Ada Lovelace"
    assert repository.saved[0].slot == "mon-9am"
    assert directory.reserved == [(Slot("mon-9am"), CustomerName("Ada Lovelace"))]


def test_a_slot_taken_between_choice_and_confirm_reoffers_fresh_slots() -> None:
    directory = MemorySlotDirectory((Slot("mon-9am"), Slot("tue-2pm")))
    repository = MemoryBookingRepository()
    service = BookingService(directory, repository)
    booking = service.begin()
    service.execute(booking, ToolName.PROVIDE_NAME, {"name": "Ada"})
    service.execute(booking, ToolName.CHOOSE_SLOT, {"slot": "mon-9am"})

    directory.slots.remove(Slot("mon-9am"))
    with pytest.raises(DomainError) as excinfo:
        service.execute(booking, ToolName.CONFIRM_BOOKING, {})

    assert excinfo.value.kind is DomainKind.CONFLICT
    assert "tue-2pm" in excinfo.value.message
    assert booking.step() is Step.CHOOSE_SLOT
    assert booking.offered_slots() == (Slot("tue-2pm"),)
    assert repository.saved == []

    service.execute(booking, ToolName.CHOOSE_SLOT, {"slot": "tue-2pm"})
    service.execute(booking, ToolName.CONFIRM_BOOKING, {})
    assert booking.step() is Step.BOOKED


def test_a_conflict_with_no_remaining_slots_is_not_found() -> None:
    directory = MemorySlotDirectory((Slot("mon-9am"),))
    repository = MemoryBookingRepository()
    service = BookingService(directory, repository)
    booking = service.begin()
    service.execute(booking, ToolName.PROVIDE_NAME, {"name": "Ada"})
    service.execute(booking, ToolName.CHOOSE_SLOT, {"slot": "mon-9am"})

    directory.slots.remove(Slot("mon-9am"))
    with pytest.raises(DomainError) as excinfo:
        service.execute(booking, ToolName.CONFIRM_BOOKING, {})

    assert excinfo.value.kind is DomainKind.NOT_FOUND
    assert repository.saved == []


def test_a_tool_at_the_wrong_step_is_a_validation_error() -> None:
    directory = MemorySlotDirectory((Slot("mon-9am"),))
    repository = MemoryBookingRepository()
    service = BookingService(directory, repository)
    booking = service.begin()

    with pytest.raises(DomainError) as excinfo:
        service.execute(booking, ToolName.CONFIRM_BOOKING, {})

    assert excinfo.value.kind is DomainKind.VALIDATION
    assert repository.saved == []


def test_an_infrastructure_failure_passes_through_untranslated() -> None:
    service = BookingService(DownSlotDirectory(), MemoryBookingRepository())
    booking = service.begin()

    with pytest.raises(InfraError):
        service.execute(booking, ToolName.PROVIDE_NAME, {"name": "Ada"})
