import pytest
import tesser.testing as ts

import scheduling.adapters.handlers as handlers
import scheduling.application as application
import scheduling.client as client
import scheduling.domain as domain
import voicewire


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


def test_the_tool_map_covers_exactly_the_domain_steps() -> None:
    assert set(handlers.TOOLS_FOR_STEP) == set(domain.STEPS)


def test_a_schema_for_an_unknown_tool_is_rejected() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    state = service.status(client.StatusRequest(booking_id="b1"))

    with pytest.raises(ValueError):
        handler._schema("cancel_booking", state)


def test_the_handler_satisfies_the_voicewire_contract() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")

    wired: voicewire.ToolSurface = handler
    turn: voicewire.ToolTurn = wired.begin()

    assert turn.reply == "ask the caller for their name"


def test_the_handler_owns_the_agent_instructions() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")

    assert "book an appointment" in handler.instructions()
    assert "never invent slots" in handler.instructions()


def test_the_flow_through_the_tool_surface() -> None:
    directory = MemorySlotDirectory(("mon-9am", "tue-2pm"))
    service = application.BookingService(directory, MemoryBookingRepository())
    handler = handlers.LlmToolHandler(service, "b1")

    turn = handler.begin()
    assert turn.reply == "ask the caller for their name"
    assert [schema["name"] for schema in turn.tools] == [handlers.PROVIDE_NAME]

    turn = handler.dispatch(handlers.PROVIDE_NAME, {"name": "Ada Lovelace"})
    assert turn.reply == "offer the caller the available slots"
    assert [schema["name"] for schema in turn.tools] == [handlers.CHOOSE_SLOT]

    turn = handler.dispatch(handlers.CHOOSE_SLOT, {"slot": "mon-9am"})
    assert turn.reply == "slot mon-9am selected; ask the caller to confirm"
    assert [schema["name"] for schema in turn.tools] == [
        handlers.CHOOSE_SLOT,
        handlers.CONFIRM_BOOKING,
    ]

    turn = handler.dispatch(handlers.CONFIRM_BOOKING, {})
    assert turn.reply == "booked mon-9am for Ada Lovelace"
    assert turn.tools == ()
    assert service.status(client.StatusRequest(booking_id="b1")).step == "booked"
    assert directory.reserved == [("mon-9am", "Ada Lovelace")]


def test_the_choose_slot_schema_offers_exactly_the_current_slots() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am", "tue-2pm")), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()

    turn = handler.dispatch(handlers.PROVIDE_NAME, {"name": "Ada"})
    schema = turn.tools[0]

    parameters = schema["parameters"]
    assert isinstance(parameters, dict)
    properties = parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["mon-9am", "tue-2pm"]


def test_a_taken_last_slot_names_both_the_conflict_and_the_exhaustion() -> None:
    directory = MemorySlotDirectory(("mon-9am",))
    service = application.BookingService(directory, MemoryBookingRepository())
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    handler.dispatch(handlers.PROVIDE_NAME, {"name": "Ada"})
    handler.dispatch(handlers.CHOOSE_SLOT, {"slot": "mon-9am"})

    directory.slots.remove("mon-9am")
    with pytest.raises(ValueError) as excinfo:
        handler.dispatch(handlers.CONFIRM_BOOKING, {})

    assert "taken" in str(excinfo.value)
    assert "no slots are available" in str(excinfo.value)


def test_a_confirm_at_the_wrong_step_keeps_its_own_error_and_mutates_nothing() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am", "tue-2pm")), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    handler.dispatch(handlers.PROVIDE_NAME, {"name": "Ada"})

    with pytest.raises(ValueError) as excinfo:
        handler.dispatch(handlers.CONFIRM_BOOKING, {})

    assert "choose_slot" in str(excinfo.value)
    assert "now available" not in str(excinfo.value)
    state = service.status(client.StatusRequest(booking_id="b1"))
    assert state.step == "choose_slot"
    assert state.offered_slots == ("mon-9am", "tue-2pm")


def test_a_choose_slot_before_any_offer_is_rejected_cleanly() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()

    with pytest.raises(ValueError) as excinfo:
        handler.dispatch(handlers.CHOOSE_SLOT, {"slot": "mon-9am"})

    assert "collect_name" in str(excinfo.value)


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

    turn = handler.status()
    assert turn.reply == "continue the booking"
    assert service.status(client.StatusRequest(booking_id="b1")).step == "choose_slot"
    schema = turn.tools[0]
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
