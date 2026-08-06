import pytest
import tesser.testing as ts

import scheduling.adapters.handlers as handlers
import scheduling.application as application
import scheduling.domain as domain


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

    def get(self, booking_id: str) -> application.BookingParts:
        return self.stored[booking_id]

    def save(self, booking_id: str, parts: application.BookingParts) -> None:
        self.stored[booking_id] = parts


def test_the_tool_map_covers_exactly_the_domain_steps() -> None:
    assert set(handlers.TOOLS_FOR_STEP) == set(domain.STEPS)


def test_the_flow_through_the_tool_surface() -> None:
    directory = MemorySlotDirectory(("mon-9am", "tue-2pm"))
    service = application.BookingService(directory, MemoryBookingRepository())
    handler = handlers.LlmToolHandler(service, "b1")

    state = handler.begin()
    assert [schema["name"] for schema in handler.tools(state)] == [handlers.PROVIDE_NAME]

    state = handler.dispatch(handlers.PROVIDE_NAME, {"name": "Ada Lovelace"})
    assert [schema["name"] for schema in handler.tools(state)] == [handlers.CHOOSE_SLOT]

    state = handler.dispatch(handlers.CHOOSE_SLOT, {"slot": "mon-9am"})
    assert [schema["name"] for schema in handler.tools(state)] == [
        handlers.CHOOSE_SLOT,
        handlers.CONFIRM_BOOKING,
    ]

    state = handler.dispatch(handlers.CONFIRM_BOOKING, {})
    assert state.step == "booked"
    assert handler.tools(state) == ()
    assert directory.reserved == [("mon-9am", "Ada Lovelace")]


def test_the_choose_slot_schema_offers_exactly_the_current_slots() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am", "tue-2pm")), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()

    state = handler.dispatch(handlers.PROVIDE_NAME, {"name": "Ada"})
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
    service = application.BookingService(directory, MemoryBookingRepository())
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    handler.dispatch(handlers.PROVIDE_NAME, {"name": "Ada"})
    handler.dispatch(handlers.CHOOSE_SLOT, {"slot": "mon-9am"})

    directory.slots.remove("mon-9am")
    with pytest.raises(ValueError) as excinfo:
        handler.dispatch(handlers.CONFIRM_BOOKING, {})

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
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()

    with pytest.raises(ValueError):
        handler.dispatch("cancel_booking", {})


def test_a_non_string_argument_is_rejected() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()

    with pytest.raises(ValueError):
        handler.dispatch(handlers.PROVIDE_NAME, {"name": 3})
