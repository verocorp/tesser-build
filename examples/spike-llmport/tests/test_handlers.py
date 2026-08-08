import pytest
import tesser.testing as ts

import scheduling.adapters.handlers as handlers
import scheduling.application as application
import scheduling.client as client
import scheduling.domain as domain
import srv.voice.router as router
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


def test_every_offered_tool_is_declarable_and_routable() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    offered = {name for names in handlers.TOOLS_FOR_STEP.values() for name in names}

    assert offered == set(handler._declarations)
    assert offered == {route.name for route in router.tools_for(handler)}


def test_a_tool_declaration_does_not_alias_the_schema_it_was_handed_even_nested() -> None:
    slot: dict[str, object] = {"enum": ["mon-9am"]}
    parameters: dict[str, object] = {"type": "object", "properties": {"slot": slot}}
    tool = voicewire.Tool("choose_slot", "Record the slot the caller chose.", parameters)

    parameters["type"] = "string"
    slot["enum"] = ["INBOUND-CHANGED"]
    rendered = tool.schema()
    outer = rendered["parameters"]
    assert isinstance(outer, dict)
    properties = outer["properties"]
    assert isinstance(properties, dict)
    inner = properties["slot"]
    assert isinstance(inner, dict)
    inner["enum"] = ["OUTBOUND-CHANGED"]

    assert tool.parameters == {"type": "object", "properties": {"slot": {"enum": ["mon-9am"]}}}


def test_a_drifted_tool_map_keeps_the_recoverable_error_class() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    state = service.status(client.StatusRequest(booking_id="b1"))

    with pytest.raises(ValueError):
        handler._tool("cancel_booking", state)


def test_a_tool_declaration_renders_its_wire_schema() -> None:
    tool = voicewire.Tool("provide_name", "Record the caller's full name.", {"type": "object"})

    assert tool.schema() == {
        "name": "provide_name",
        "description": "Record the caller's full name.",
        "parameters": {"type": "object"},
    }


def test_a_route_carries_the_endpoint_the_host_calls() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()

    route = router.match(router.tools_for(handler), handlers.PROVIDE_NAME)

    assert route is not None
    endpoint: voicewire.ToolEndpoint = route.endpoint
    turn = endpoint({"name": "Ada Lovelace"})
    assert turn.reply == "offer the caller the available slots"


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
    assert [tool.name for tool in turn.tools] == [handlers.PROVIDE_NAME]

    turn = handler.provide_name({"name": "Ada Lovelace"})
    assert turn.reply == "offer the caller the available slots"
    assert [tool.name for tool in turn.tools] == [handlers.CHOOSE_SLOT]

    turn = handler.choose_slot({"slot": "mon-9am"})
    assert turn.reply == "slot mon-9am selected; ask the caller to confirm"
    assert [tool.name for tool in turn.tools] == [
        handlers.CHOOSE_SLOT,
        handlers.CONFIRM_BOOKING,
    ]

    turn = handler.confirm({})
    assert turn.reply == "booked mon-9am for Ada Lovelace"
    assert turn.tools == ()
    assert service.status(client.StatusRequest(booking_id="b1")).step == "booked"
    assert directory.reserved == [("mon-9am", "Ada Lovelace")]


def test_the_provide_name_tool_declares_exactly_a_required_name() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")

    tool = handler.begin().tools[0]

    assert tool.name == handlers.PROVIDE_NAME
    assert tool.description == "Record the caller's full name."
    assert tool.parameters == {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }


def test_the_confirm_booking_tool_declares_no_arguments() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    handler.provide_name({"name": "Ada"})

    turn = handler.choose_slot({"slot": "mon-9am"})
    tool = turn.tools[1]

    assert tool.name == handlers.CONFIRM_BOOKING
    assert tool.parameters == {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }


def test_a_tool_declaration_is_frozen_and_compares_by_value() -> None:
    tool = voicewire.Tool("provide_name", "Record the caller's full name.", {"type": "object"})

    assert tool == voicewire.Tool(
        "provide_name", "Record the caller's full name.", {"type": "object"}
    )
    assert tool != voicewire.Tool("choose_slot", "Record the caller's full name.", {"type": "object"})
    with pytest.raises(AttributeError):
        tool.name = "cancel_booking"


def test_the_choose_slot_schema_offers_exactly_the_current_slots() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am", "tue-2pm")), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()

    turn = handler.provide_name({"name": "Ada"})
    tool = turn.tools[0]

    properties = tool.parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["mon-9am", "tue-2pm"]


def test_a_taken_last_slot_names_both_the_conflict_and_the_exhaustion() -> None:
    directory = MemorySlotDirectory(("mon-9am",))
    service = application.BookingService(directory, MemoryBookingRepository())
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    handler.provide_name({"name": "Ada"})
    handler.choose_slot({"slot": "mon-9am"})

    directory.slots.remove("mon-9am")
    with pytest.raises(ValueError) as excinfo:
        handler.confirm({})

    assert "taken" in str(excinfo.value)
    assert "no slots are available" in str(excinfo.value)


def test_a_confirm_at_the_wrong_step_keeps_its_own_error_and_mutates_nothing() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am", "tue-2pm")), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    handler.provide_name({"name": "Ada"})

    with pytest.raises(ValueError) as excinfo:
        handler.confirm({})

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
        handler.choose_slot({"slot": "mon-9am"})

    assert "collect_name" in str(excinfo.value)


def test_a_taken_slot_reoffers_and_names_the_fresh_slots() -> None:
    directory = MemorySlotDirectory(("mon-9am", "tue-2pm"))
    service = application.BookingService(directory, MemoryBookingRepository())
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    handler.provide_name({"name": "Ada"})
    handler.choose_slot({"slot": "mon-9am"})

    directory.slots.remove("mon-9am")
    with pytest.raises(ValueError) as excinfo:
        handler.confirm({})

    assert "now available: tue-2pm" in str(excinfo.value)

    turn = handler.status()
    assert turn.reply == "continue the booking"
    assert service.status(client.StatusRequest(booking_id="b1")).step == "choose_slot"
    tool = turn.tools[0]
    properties = tool.parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["tue-2pm"]


def test_an_unroutable_tool_name_has_no_endpoint() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")

    assert router.match(router.tools_for(handler), "cancel_booking") is None


def test_a_non_string_argument_is_rejected() -> None:
    service = application.BookingService(
        MemorySlotDirectory(("mon-9am",)), MemoryBookingRepository()
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()

    with pytest.raises(ValueError):
        handler.provide_name({"name": 3})
