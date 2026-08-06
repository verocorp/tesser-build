import pytest

from scheduling.adapters.handlers import (
    CHOOSE_SLOT,
    CONFIRM_BOOKING,
    PROVIDE_NAME,
    TOOLS_FOR_STEP,
    LlmToolHandler,
)
from scheduling.application import BookingService
from scheduling.domain import STEPS
from tests.fakes import MemoryBookingRepository, MemorySlotDirectory


def test_the_tool_map_covers_exactly_the_domain_steps() -> None:
    assert set(TOOLS_FOR_STEP) == set(STEPS)


def test_the_flow_through_the_tool_surface() -> None:
    directory = MemorySlotDirectory(("mon-9am", "tue-2pm"))
    service = BookingService(directory, MemoryBookingRepository())
    handler = LlmToolHandler(service, "b1")

    state = handler.begin()
    assert [schema["name"] for schema in handler.tools(state)] == [PROVIDE_NAME]

    state = handler.dispatch(PROVIDE_NAME, {"name": "Ada Lovelace"})
    assert [schema["name"] for schema in handler.tools(state)] == [CHOOSE_SLOT]

    state = handler.dispatch(CHOOSE_SLOT, {"slot": "mon-9am"})
    assert [schema["name"] for schema in handler.tools(state)] == [
        CHOOSE_SLOT,
        CONFIRM_BOOKING,
    ]

    state = handler.dispatch(CONFIRM_BOOKING, {})
    assert state.step == "booked"
    assert handler.tools(state) == ()
    assert directory.reserved == [("mon-9am", "Ada Lovelace")]


def test_the_choose_slot_schema_offers_exactly_the_current_slots() -> None:
    service = BookingService(
        MemorySlotDirectory(("mon-9am", "tue-2pm")), MemoryBookingRepository()
    )
    handler = LlmToolHandler(service, "b1")
    handler.begin()

    state = handler.dispatch(PROVIDE_NAME, {"name": "Ada"})
    schema = handler.tools(state)[0]

    parameters = schema["parameters"]
    assert isinstance(parameters, dict)
    properties = parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["mon-9am", "tue-2pm"]


def test_a_taken_slot_reoffers_and_names_the_fresh_slots() -> None:
    directory = MemorySlotDirectory(("mon-9am", "tue-2pm"))
    service = BookingService(directory, MemoryBookingRepository())
    handler = LlmToolHandler(service, "b1")
    handler.begin()
    handler.dispatch(PROVIDE_NAME, {"name": "Ada"})
    handler.dispatch(CHOOSE_SLOT, {"slot": "mon-9am"})

    directory.slots.remove("mon-9am")
    with pytest.raises(ValueError) as excinfo:
        handler.dispatch(CONFIRM_BOOKING, {})

    assert "now available: tue-2pm" in str(excinfo.value)

    state = handler.status()
    assert state.step == "choose_slot"
    schema = handler.tools(state)[0]
    parameters = schema["parameters"]
    assert isinstance(parameters, dict)
    properties = parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["tue-2pm"]


def test_an_unknown_tool_is_rejected() -> None:
    service = BookingService(MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository())
    handler = LlmToolHandler(service, "b1")
    handler.begin()

    with pytest.raises(ValueError):
        handler.dispatch("cancel_booking", {})


def test_a_non_string_argument_is_rejected() -> None:
    service = BookingService(MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository())
    handler = LlmToolHandler(service, "b1")
    handler.begin()

    with pytest.raises(ValueError):
        handler.dispatch(PROVIDE_NAME, {"name": 3})
