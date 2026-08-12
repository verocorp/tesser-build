import pytest
import tesser.testing as ts

import scheduling.adapters.directory_memory as directory_memory
import scheduling.adapters.handlers as handlers
import scheduling.adapters.repo_memory as repo_memory
import scheduling.application.service as application
import scheduling.client.client as client
import scheduling.domain.scheduling as domain
import srv.voice.router as router  # tessercheck:ignore TB070
import protocol.voice as voice


@ts.fake
class FakeSchedulingClientScripted(client.SchedulingClient):
    def __init__(self, *states: client.BookingStateResponse) -> None:
        self.pending = list(states)
        self.requests: list[object] = []

    def _next(self, request: object) -> client.BookingStateResponse:
        self.requests.append(request)
        return self.pending.pop(0)

    def begin(self, request: client.BeginBookingRequest) -> client.BookingStateResponse:
        return self._next(request)

    def provide_name(self, request: client.ProvideNameRequest) -> client.BookingStateResponse:
        return self._next(request)

    def choose_slot(self, request: client.ChooseSlotRequest) -> client.BookingStateResponse:
        return self._next(request)

    def confirm(self, request: client.ConfirmBookingRequest) -> client.BookingStateResponse:
        return self._next(request)

    def status(self, request: client.StatusRequest) -> client.BookingStateResponse:
        return self._next(request)


def test_the_tool_map_covers_exactly_the_domain_steps() -> None:
    assert set(handlers.TOOLS_FOR_STEP) == set(domain.STEPS)


def test_every_offered_tool_is_declarable_and_routable() -> None:
    handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(), "b1")
    offered = {name for names in handlers.TOOLS_FOR_STEP.values() for name in names}

    assert offered == set(handler._declarations)
    assert offered == {route.name for route in router.tools_for(handler)}


def test_a_tool_call_does_not_alias_the_arguments_it_was_handed() -> None:
    arguments: dict[str, object] = {"name": "Ada", "nested": {"a": 1}}

    call = voice.ToolCall("provide_name", arguments)
    arguments["name"] = "Eve"
    nested = arguments["nested"]
    assert isinstance(nested, dict)
    nested["a"] = 2

    assert call.arguments == {"name": "Ada", "nested": {"a": 1}}


def test_a_tool_declaration_does_not_alias_the_schema_it_was_handed_even_nested() -> None:
    slot: dict[str, object] = {"enum": ["mon-9am"]}
    parameters: dict[str, object] = {"type": "object", "properties": {"slot": slot}}
    tool = voice.Tool("choose_slot", "Record the slot the caller chose.", parameters)

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
    handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(), "b1")

    with pytest.raises(ValueError):
        handler._tool("cancel_booking", client.BookingStateResponse(step="collect_name", offered_slots=(), reply="ask the caller for their name"))


def test_a_tool_declaration_renders_its_wire_schema() -> None:
    tool = voice.Tool("provide_name", "Record the caller's full name.", {"type": "object"})

    assert tool.schema() == {
        "name": "provide_name",
        "description": "Record the caller's full name.",
        "parameters": {"type": "object"},
    }


def test_a_route_carries_the_endpoint_the_host_calls() -> None:
    scripted = FakeSchedulingClientScripted(client.BookingStateResponse(step="choose_slot", offered_slots=("mon-9am", "tue-2pm"), reply="offer the caller the available slots"))
    handler = handlers.LlmToolHandler(scripted, "b1")

    route = router.match(router.tools_for(handler), handlers.PROVIDE_NAME)

    assert route is not None
    endpoint: voice.ToolEndpoint = route.endpoint
    turn = endpoint(voice.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada Lovelace"}))
    assert [tool.name for tool in turn.tools] == [handlers.CHOOSE_SLOT]
    request = scripted.requests[0]
    assert isinstance(request, client.ProvideNameRequest)
    assert request.booking_id == "b1"
    assert request.name == "Ada Lovelace"


def test_the_handler_satisfies_the_voicewire_contract() -> None:
    handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(client.BookingStateResponse(step="collect_name", offered_slots=(), reply="ask the caller for their name")), "b1")

    wired: voice.ToolSurface = handler
    turn: voice.ToolTurn = wired.begin()

    assert turn.reply == "ask the caller for their name"


def test_the_handler_owns_the_agent_instructions() -> None:
    handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(), "b1")

    assert "book an appointment" in handler.instructions()
    assert "never invent slots" in handler.instructions()


def test_a_turn_carries_the_reply_and_the_tools_for_the_step() -> None:
    scripted = FakeSchedulingClientScripted(client.BookingStateResponse(step="confirm", offered_slots=("mon-9am",), reply="ask the caller to confirm"))
    handler = handlers.LlmToolHandler(scripted, "b1")

    turn = handler.begin()

    assert turn.reply == "ask the caller to confirm"
    assert [tool.name for tool in turn.tools] == [
        handlers.CHOOSE_SLOT,
        handlers.CONFIRM_BOOKING,
    ]


def test_the_provide_name_tool_declares_exactly_a_required_name() -> None:
    handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(client.BookingStateResponse(step="collect_name", offered_slots=(), reply="ask the caller for their name")), "b1")

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
    handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(client.BookingStateResponse(step="confirm", offered_slots=("mon-9am",), reply="ask the caller to confirm")), "b1")

    turn = handler.begin()
    tool = turn.tools[1]

    assert tool.name == handlers.CONFIRM_BOOKING
    assert tool.parameters == {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }


def test_a_tool_declaration_is_frozen_and_compares_by_value() -> None:
    tool = voice.Tool("provide_name", "Record the caller's full name.", {"type": "object"})

    assert tool == voice.Tool(
        "provide_name", "Record the caller's full name.", {"type": "object"}
    )
    assert tool != voice.Tool("choose_slot", "Record the caller's full name.", {"type": "object"})
    with pytest.raises(AttributeError):
        tool.name = "cancel_booking"


def test_the_choose_slot_schema_offers_exactly_the_current_slots() -> None:
    handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(client.BookingStateResponse(step="choose_slot", offered_slots=("mon-9am", "tue-2pm"), reply="offer the caller the available slots")), "b1")

    turn = handler.begin()
    tool = turn.tools[0]

    properties = tool.parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["mon-9am", "tue-2pm"]


def test_an_unroutable_tool_name_has_no_endpoint() -> None:
    handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(), "b1")

    assert router.match(router.tools_for(handler), "cancel_booking") is None


def test_a_non_string_argument_is_rejected_with_the_wire_word() -> None:
    scripted = FakeSchedulingClientScripted()
    handler = handlers.LlmToolHandler(scripted, "b1")

    with pytest.raises(voice.BadToolCall):
        handler.provide_name(voice.ToolCall(handlers.PROVIDE_NAME, {"name": 3}))

    assert scripted.requests == []


def test_the_flow_through_the_tool_surface() -> None:
    directory = directory_memory.MemorySlotDirectory(("mon-9am", "tue-2pm"))
    service = application.BookingService(directory, repo_memory.MemoryBookingRepository())
    handler = handlers.LlmToolHandler(service, "b1")

    turn = handler.begin()
    assert turn.reply == "ask the caller for their name"
    assert [tool.name for tool in turn.tools] == [handlers.PROVIDE_NAME]

    turn = handler.provide_name(voice.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada Lovelace"}))
    assert turn.reply == "offer the caller the available slots"
    assert [tool.name for tool in turn.tools] == [handlers.CHOOSE_SLOT]

    turn = handler.choose_slot(voice.ToolCall(handlers.CHOOSE_SLOT, {"slot": "mon-9am"}))
    assert turn.reply == "slot mon-9am selected; ask the caller to confirm"
    assert [tool.name for tool in turn.tools] == [
        handlers.CHOOSE_SLOT,
        handlers.CONFIRM_BOOKING,
    ]

    turn = handler.confirm(voice.ToolCall(handlers.CONFIRM_BOOKING, {}))
    assert turn.reply == "booked mon-9am for Ada Lovelace"
    assert turn.tools == ()
    assert service.status(client.StatusRequest(booking_id="b1")).step == "booked"
    assert directory.reserved == [("mon-9am", "Ada Lovelace")]


def test_a_taken_last_slot_with_nothing_to_reoffer_reaches_the_model_as_an_error() -> None:
    directory = directory_memory.MemorySlotDirectory(("mon-9am",))
    service = application.BookingService(directory, repo_memory.MemoryBookingRepository())
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    handler.provide_name(voice.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada"}))
    handler.choose_slot(voice.ToolCall(handlers.CHOOSE_SLOT, {"slot": "mon-9am"}))

    directory.slots.remove("mon-9am")
    with pytest.raises(ValueError) as excinfo:
        handler.confirm(voice.ToolCall(handlers.CONFIRM_BOOKING, {}))

    assert "no slots are available" in str(excinfo.value)


def test_a_confirm_at_the_wrong_step_keeps_its_own_error_and_mutates_nothing() -> None:
    service = application.BookingService(
        directory_memory.MemorySlotDirectory(("mon-9am", "tue-2pm")),
        repo_memory.MemoryBookingRepository(),
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    handler.provide_name(voice.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada"}))

    with pytest.raises(ValueError) as excinfo:
        handler.confirm(voice.ToolCall(handlers.CONFIRM_BOOKING, {}))

    assert "choose_slot" in str(excinfo.value)
    assert "now available" not in str(excinfo.value)
    state = service.status(client.StatusRequest(booking_id="b1"))
    assert state.step == "choose_slot"
    assert state.offered_slots == ("mon-9am", "tue-2pm")


def test_a_choose_slot_before_any_offer_is_rejected_cleanly() -> None:
    service = application.BookingService(
        directory_memory.MemorySlotDirectory(("mon-9am",)),
        repo_memory.MemoryBookingRepository(),
    )
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()

    with pytest.raises(ValueError) as excinfo:
        handler.choose_slot(voice.ToolCall(handlers.CHOOSE_SLOT, {"slot": "mon-9am"}))

    assert "collect_name" in str(excinfo.value)


def test_a_taken_slot_comes_back_as_one_turn_offering_the_fresh_slots() -> None:
    directory = directory_memory.MemorySlotDirectory(("mon-9am", "tue-2pm"))
    service = application.BookingService(directory, repo_memory.MemoryBookingRepository())
    handler = handlers.LlmToolHandler(service, "b1")
    handler.begin()
    handler.provide_name(voice.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada"}))
    handler.choose_slot(voice.ToolCall(handlers.CHOOSE_SLOT, {"slot": "mon-9am"}))

    directory.slots.remove("mon-9am")
    turn = handler.confirm(voice.ToolCall(handlers.CONFIRM_BOOKING, {}))

    assert turn.reply == "mon-9am was just taken; offer the caller the updated slots"
    assert service.status(client.StatusRequest(booking_id="b1")).step == "choose_slot"
    assert [tool.name for tool in turn.tools] == [handlers.CHOOSE_SLOT]
    tool = turn.tools[0]
    properties = tool.parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["tue-2pm"]
