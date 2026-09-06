import pytest
import tesser.testing as ts

import protocol
import scheduling.adapters.gateways as gateways
import scheduling.adapters.handlers as handlers
import scheduling.adapters.repositories as repositories
import scheduling.application as application
import scheduling.client as client
import scheduling.domain as domain


@ts.fake
class FakeSchedulingClientScripted(client.SchedulingClient):
    def __init__(self, *states: client.BookingStateResponse) -> None:
        self.pending = list(states)
        self.requests: list[object] = []

    def begin(
        self, begin_booking_request: client.BeginBookingRequest
    ) -> client.BookingStateResponse:
        self.requests.append(begin_booking_request)
        return self.pending.pop(0)

    def provide_name(
        self, provide_name_request: client.ProvideNameRequest
    ) -> client.BookingStateResponse:
        self.requests.append(provide_name_request)
        return self.pending.pop(0)

    def choose_slot(
        self, choose_slot_request: client.ChooseSlotRequest
    ) -> client.BookingStateResponse:
        self.requests.append(choose_slot_request)
        return self.pending.pop(0)

    def confirm(
        self, confirm_booking_request: client.ConfirmBookingRequest
    ) -> client.BookingStateResponse:
        self.requests.append(confirm_booking_request)
        return self.pending.pop(0)

    def status(
        self, status_request: client.StatusRequest
    ) -> client.BookingStateResponse:
        self.requests.append(status_request)
        return self.pending.pop(0)


def test_the_tool_map_covers_exactly_the_domain_steps() -> None:
    assert set(handlers.TOOLS_FOR_STEP) == set(domain.STEPS)


def test_every_offered_tool_is_declarable_and_routable() -> None:
    llm_tool_handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(), "b1")
    offered = {name for names in handlers.TOOLS_FOR_STEP.values() for name in names}

    assert offered == set(llm_tool_handler._declarations)
    routes = (
        protocol.Route(handlers.PROVIDE_NAME, llm_tool_handler.provide_name),
        protocol.Route(handlers.CHOOSE_SLOT, llm_tool_handler.choose_slot),
        protocol.Route(handlers.CONFIRM_BOOKING, llm_tool_handler.confirm),
    )
    assert offered == {route.name for route in routes}


def test_a_tool_call_does_not_alias_the_arguments_it_was_handed() -> None:
    arguments: dict[str, object] = {"name": "Ada", "nested": {"a": 1}}

    tool_call = protocol.ToolCall("provide_name", arguments)
    arguments["name"] = "Eve"
    nested = arguments["nested"]
    assert isinstance(nested, dict)
    nested["a"] = 2

    assert tool_call.arguments == {"name": "Ada", "nested": {"a": 1}}


def test_a_tool_declaration_does_not_alias_the_schema_it_was_handed_even_nested() -> None:
    slot: dict[str, object] = {"enum": ["mon-9am"]}
    parameters: dict[str, object] = {"type": "object", "properties": {"slot": slot}}
    tool = protocol.Tool("choose_slot", "Record the slot the caller chose.", parameters)

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


def test_a_tool_declaration_renders_its_wire_schema() -> None:
    tool = protocol.Tool("provide_name", "Record the caller's full name.", {"type": "object"})

    assert tool.schema() == {
        "name": "provide_name",
        "description": "Record the caller's full name.",
        "parameters": {"type": "object"},
    }


def test_a_route_carries_the_endpoint_the_host_calls() -> None:
    fake_scheduling_client_scripted = FakeSchedulingClientScripted(
        client.BookingStateResponse(
            step="choose_slot",
            offered_slots=("mon-9am", "tue-2pm"),
            reply="offer the caller the available slots",
        )
    )
    llm_tool_handler = handlers.LlmToolHandler(fake_scheduling_client_scripted, "b1")

    routes = (
        protocol.Route(handlers.PROVIDE_NAME, llm_tool_handler.provide_name),
        protocol.Route(handlers.CHOOSE_SLOT, llm_tool_handler.choose_slot),
        protocol.Route(handlers.CONFIRM_BOOKING, llm_tool_handler.confirm),
    )
    route: protocol.Route | None = None
    for candidate in routes:
        if candidate.name == handlers.PROVIDE_NAME:
            route = candidate
            break

    assert route is not None
    endpoint: protocol.ToolEndpoint = route.endpoint
    tool_turn = endpoint(protocol.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada Lovelace"}))
    assert [tool.name for tool in tool_turn.tools] == [handlers.CHOOSE_SLOT]
    request = fake_scheduling_client_scripted.requests[0]
    assert isinstance(request, client.ProvideNameRequest)
    assert request.booking_id == "b1"
    assert request.name == "Ada Lovelace"


def test_the_handler_satisfies_the_voicewire_contract() -> None:
    llm_tool_handler = handlers.LlmToolHandler(
        FakeSchedulingClientScripted(
            client.BookingStateResponse(
                step="collect_name", offered_slots=(), reply="ask the caller for their name"
            )
        ),
        "b1",
    )

    wired: protocol.ToolSurface = llm_tool_handler
    tool_turn: protocol.ToolTurn = wired.begin()

    assert tool_turn.reply == "ask the caller for their name"


def test_the_handler_owns_the_agent_instructions() -> None:
    llm_tool_handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(), "b1")

    assert "book an appointment" in llm_tool_handler.instructions()
    assert "never invent slots" in llm_tool_handler.instructions()


def test_a_turn_carries_the_reply_and_the_tools_for_the_step() -> None:
    fake_scheduling_client_scripted = FakeSchedulingClientScripted(
        client.BookingStateResponse(
            step="confirm", offered_slots=("mon-9am",), reply="ask the caller to confirm"
        )
    )
    llm_tool_handler = handlers.LlmToolHandler(fake_scheduling_client_scripted, "b1")

    tool_turn = llm_tool_handler.begin()

    assert tool_turn.reply == "ask the caller to confirm"
    assert [tool.name for tool in tool_turn.tools] == [
        handlers.CHOOSE_SLOT,
        handlers.CONFIRM_BOOKING,
    ]


def test_the_provide_name_tool_declares_exactly_a_required_name() -> None:
    llm_tool_handler = handlers.LlmToolHandler(
        FakeSchedulingClientScripted(
            client.BookingStateResponse(
                step="collect_name", offered_slots=(), reply="ask the caller for their name"
            )
        ),
        "b1",
    )

    tool = llm_tool_handler.begin().tools[0]

    assert tool.name == handlers.PROVIDE_NAME
    assert tool.description == "Record the caller's full name."
    assert tool.parameters == {
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
        "additionalProperties": False,
    }


def test_the_confirm_booking_tool_declares_no_arguments() -> None:
    llm_tool_handler = handlers.LlmToolHandler(
        FakeSchedulingClientScripted(
            client.BookingStateResponse(
                step="confirm", offered_slots=("mon-9am",), reply="ask the caller to confirm"
            )
        ),
        "b1",
    )

    tool_turn = llm_tool_handler.begin()
    tool = tool_turn.tools[1]

    assert tool.name == handlers.CONFIRM_BOOKING
    assert tool.parameters == {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }


def test_a_tool_declaration_is_frozen_and_compares_by_value() -> None:
    tool = protocol.Tool("provide_name", "Record the caller's full name.", {"type": "object"})

    assert tool == protocol.Tool(
        "provide_name", "Record the caller's full name.", {"type": "object"}
    )
    assert tool != protocol.Tool(
        "choose_slot", "Record the caller's full name.", {"type": "object"}
    )
    with pytest.raises(AttributeError):
        tool.name = "cancel_booking"


def test_the_choose_slot_schema_offers_exactly_the_current_slots() -> None:
    llm_tool_handler = handlers.LlmToolHandler(
        FakeSchedulingClientScripted(
            client.BookingStateResponse(
                step="choose_slot",
                offered_slots=("mon-9am", "tue-2pm"),
                reply="offer the caller the available slots",
            )
        ),
        "b1",
    )

    tool_turn = llm_tool_handler.begin()
    tool = tool_turn.tools[0]

    properties = tool.parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["mon-9am", "tue-2pm"]


def test_an_unroutable_tool_name_has_no_endpoint() -> None:
    llm_tool_handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(), "b1")

    routes = (
        protocol.Route(handlers.PROVIDE_NAME, llm_tool_handler.provide_name),
        protocol.Route(handlers.CHOOSE_SLOT, llm_tool_handler.choose_slot),
        protocol.Route(handlers.CONFIRM_BOOKING, llm_tool_handler.confirm),
    )
    matched: protocol.Route | None = None
    for candidate in routes:
        if candidate.name == "cancel_booking":
            matched = candidate
            break

    assert matched is None


def test_a_non_string_argument_is_rejected_with_the_wire_word() -> None:
    fake_scheduling_client_scripted = FakeSchedulingClientScripted()
    llm_tool_handler = handlers.LlmToolHandler(fake_scheduling_client_scripted, "b1")

    with pytest.raises(protocol.BadToolCall):
        llm_tool_handler.provide_name(
            protocol.ToolCall(handlers.PROVIDE_NAME, {"name": 3})
        )

    assert fake_scheduling_client_scripted.requests == []


def test_the_flow_through_the_tool_surface() -> None:
    memory_slot_directory = gateways.MemorySlotDirectory(("mon-9am", "tue-2pm"))
    booking_service = application.BookingService(
        memory_slot_directory, repositories.MemoryBookingRepository()
    )
    llm_tool_handler = handlers.LlmToolHandler(booking_service, "b1")

    tool_turn = llm_tool_handler.begin()
    assert tool_turn.reply == "ask the caller for their name"
    assert [tool.name for tool in tool_turn.tools] == [handlers.PROVIDE_NAME]

    tool_turn = llm_tool_handler.provide_name(
        protocol.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada Lovelace"})
    )
    assert tool_turn.reply == "offer the caller the available slots"
    assert [tool.name for tool in tool_turn.tools] == [handlers.CHOOSE_SLOT]

    tool_turn = llm_tool_handler.choose_slot(
        protocol.ToolCall(handlers.CHOOSE_SLOT, {"slot": "mon-9am"})
    )
    assert tool_turn.reply == "slot mon-9am selected; ask the caller to confirm"
    assert [tool.name for tool in tool_turn.tools] == [
        handlers.CHOOSE_SLOT,
        handlers.CONFIRM_BOOKING,
    ]

    tool_turn = llm_tool_handler.confirm(protocol.ToolCall(handlers.CONFIRM_BOOKING, {}))
    assert tool_turn.reply == "booked mon-9am for Ada Lovelace"
    assert tool_turn.tools == ()
    assert booking_service.status(client.StatusRequest(booking_id="b1")).step == "booked"
    assert memory_slot_directory.reserved == [("mon-9am", "Ada Lovelace")]


def test_a_taken_last_slot_with_nothing_to_reoffer_reaches_the_model_as_an_error() -> None:
    memory_slot_directory = gateways.MemorySlotDirectory(("mon-9am",))
    booking_service = application.BookingService(
        memory_slot_directory, repositories.MemoryBookingRepository()
    )
    llm_tool_handler = handlers.LlmToolHandler(booking_service, "b1")
    llm_tool_handler.begin()
    llm_tool_handler.provide_name(protocol.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada"}))
    llm_tool_handler.choose_slot(
        protocol.ToolCall(handlers.CHOOSE_SLOT, {"slot": "mon-9am"})
    )

    memory_slot_directory.slots.remove("mon-9am")
    with pytest.raises(ValueError) as excinfo:
        llm_tool_handler.confirm(protocol.ToolCall(handlers.CONFIRM_BOOKING, {}))

    assert "no slots are available" in str(excinfo.value)


def test_a_confirm_at_the_wrong_step_keeps_its_own_error_and_mutates_nothing() -> None:
    booking_service = application.BookingService(
        gateways.MemorySlotDirectory(("mon-9am", "tue-2pm")),
        repositories.MemoryBookingRepository(),
    )
    llm_tool_handler = handlers.LlmToolHandler(booking_service, "b1")
    llm_tool_handler.begin()
    llm_tool_handler.provide_name(protocol.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada"}))

    with pytest.raises(ValueError) as excinfo:
        llm_tool_handler.confirm(protocol.ToolCall(handlers.CONFIRM_BOOKING, {}))

    assert "choose_slot" in str(excinfo.value)
    assert "now available" not in str(excinfo.value)
    booking_state_response = booking_service.status(client.StatusRequest(booking_id="b1"))
    assert booking_state_response.step == "choose_slot"
    assert booking_state_response.offered_slots == ("mon-9am", "tue-2pm")


def test_a_choose_slot_before_any_offer_is_rejected_cleanly() -> None:
    booking_service = application.BookingService(
        gateways.MemorySlotDirectory(("mon-9am",)),
        repositories.MemoryBookingRepository(),
    )
    llm_tool_handler = handlers.LlmToolHandler(booking_service, "b1")
    llm_tool_handler.begin()

    with pytest.raises(ValueError) as excinfo:
        llm_tool_handler.choose_slot(
            protocol.ToolCall(handlers.CHOOSE_SLOT, {"slot": "mon-9am"})
        )

    assert "collect_name" in str(excinfo.value)


def test_a_taken_slot_comes_back_as_one_turn_offering_the_fresh_slots() -> None:
    memory_slot_directory = gateways.MemorySlotDirectory(("mon-9am", "tue-2pm"))
    booking_service = application.BookingService(
        memory_slot_directory, repositories.MemoryBookingRepository()
    )
    llm_tool_handler = handlers.LlmToolHandler(booking_service, "b1")
    llm_tool_handler.begin()
    llm_tool_handler.provide_name(protocol.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada"}))
    llm_tool_handler.choose_slot(
        protocol.ToolCall(handlers.CHOOSE_SLOT, {"slot": "mon-9am"})
    )

    memory_slot_directory.slots.remove("mon-9am")
    tool_turn = llm_tool_handler.confirm(protocol.ToolCall(handlers.CONFIRM_BOOKING, {}))

    assert tool_turn.reply == "mon-9am was just taken; offer the caller the updated slots"
    assert booking_service.status(client.StatusRequest(booking_id="b1")).step == "choose_slot"
    assert [tool.name for tool in tool_turn.tools] == [handlers.CHOOSE_SLOT]
    tool = tool_turn.tools[0]
    properties = tool.parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["tue-2pm"]
