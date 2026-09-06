from __future__ import annotations

import pytest
import tesser.testing as ts

import protocol
import scheduling.adapters.handlers as handlers
import scheduling.client as client


@ts.fake
class FakeSchedulingClientScripted(client.SchedulingClient):

    def __init__(
        self, *states: client.BookingStateResponse, error: Exception | None = None
    ) -> None:
        self.pending = list(states)
        self.error = error
        self.requests: list[object] = []

    def begin(
        self, begin_booking_request: client.BeginBookingRequest
    ) -> client.BookingStateResponse:
        self.requests.append(begin_booking_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def provide_name(
        self, provide_name_request: client.ProvideNameRequest
    ) -> client.BookingStateResponse:
        self.requests.append(provide_name_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def choose_slot(
        self, choose_slot_request: client.ChooseSlotRequest
    ) -> client.BookingStateResponse:
        self.requests.append(choose_slot_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def confirm(
        self, confirm_booking_request: client.ConfirmBookingRequest
    ) -> client.BookingStateResponse:
        self.requests.append(confirm_booking_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)

    def status(
        self, status_request: client.StatusRequest
    ) -> client.BookingStateResponse:
        self.requests.append(status_request)
        if self.error is not None:
            raise self.error
        return self.pending.pop(0)


def test_the_handler_carries_the_instructions_the_model_opens_with() -> None:
    llm_tool_handler = handlers.LlmToolHandler(FakeSchedulingClientScripted(), "b1")

    assert "book an appointment" in llm_tool_handler.instructions()
    assert "never invent slots" in llm_tool_handler.instructions()


def test_beginning_asks_the_client_for_its_own_booking() -> None:
    fake_scheduling_client_scripted = FakeSchedulingClientScripted(
        client.BookingStateResponse(
            step="collect_name", offered_slots=(), reply="ask the caller for their name"
        )
    )
    llm_tool_handler = handlers.LlmToolHandler(fake_scheduling_client_scripted, "b7")

    tool_turn = llm_tool_handler.begin()

    assert tool_turn.reply == "ask the caller for their name"
    request = fake_scheduling_client_scripted.requests[0]
    assert isinstance(request, client.BeginBookingRequest)
    assert request.booking_id == "b7"


def test_asking_for_status_reads_the_same_booking() -> None:
    fake_scheduling_client_scripted = FakeSchedulingClientScripted(
        client.BookingStateResponse(
            step="choose_slot", offered_slots=("mon-9am",), reply="continue the booking"
        )
    )
    llm_tool_handler = handlers.LlmToolHandler(fake_scheduling_client_scripted, "b7")

    tool_turn = llm_tool_handler.status()

    assert tool_turn.reply == "continue the booking"
    request = fake_scheduling_client_scripted.requests[0]
    assert isinstance(request, client.StatusRequest)
    assert request.booking_id == "b7"


def test_the_name_the_model_supplied_reaches_the_client() -> None:
    fake_scheduling_client_scripted = FakeSchedulingClientScripted(
        client.BookingStateResponse(
            step="choose_slot",
            offered_slots=("mon-9am",),
            reply="offer the caller the available slots",
        )
    )
    llm_tool_handler = handlers.LlmToolHandler(fake_scheduling_client_scripted, "b1")

    llm_tool_handler.provide_name(
        protocol.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada Lovelace"})
    )

    request = fake_scheduling_client_scripted.requests[0]
    assert isinstance(request, client.ProvideNameRequest)
    assert request.booking_id == "b1"
    assert request.name == "Ada Lovelace"


def test_the_slot_the_model_supplied_reaches_the_client() -> None:
    fake_scheduling_client_scripted = FakeSchedulingClientScripted(
        client.BookingStateResponse(
            step="confirm", offered_slots=("mon-9am",), reply="ask the caller to confirm"
        )
    )
    llm_tool_handler = handlers.LlmToolHandler(fake_scheduling_client_scripted, "b1")

    llm_tool_handler.choose_slot(
        protocol.ToolCall(handlers.CHOOSE_SLOT, {"slot": "mon-9am"})
    )

    request = fake_scheduling_client_scripted.requests[0]
    assert isinstance(request, client.ChooseSlotRequest)
    assert request.slot == "mon-9am"


def test_confirming_carries_no_argument_beyond_the_booking() -> None:
    fake_scheduling_client_scripted = FakeSchedulingClientScripted(
        client.BookingStateResponse(
            step="booked", offered_slots=(), reply="booked mon-9am for Ada"
        )
    )
    llm_tool_handler = handlers.LlmToolHandler(fake_scheduling_client_scripted, "b1")

    tool_turn = llm_tool_handler.confirm(
        protocol.ToolCall(handlers.CONFIRM_BOOKING, {})
    )

    assert tool_turn.reply == "booked mon-9am for Ada"
    request = fake_scheduling_client_scripted.requests[0]
    assert isinstance(request, client.ConfirmBookingRequest)
    assert request.booking_id == "b1"


def test_a_non_string_argument_never_reaches_the_client() -> None:
    fake_scheduling_client_scripted = FakeSchedulingClientScripted()
    llm_tool_handler = handlers.LlmToolHandler(fake_scheduling_client_scripted, "b1")

    with pytest.raises(protocol.BadToolCall):
        llm_tool_handler.provide_name(
            protocol.ToolCall(handlers.PROVIDE_NAME, {"name": 3})
        )

    assert fake_scheduling_client_scripted.requests == []


def test_a_booked_booking_offers_the_model_no_further_tool() -> None:
    llm_tool_handler = handlers.LlmToolHandler(
        FakeSchedulingClientScripted(
            client.BookingStateResponse(
                step="booked", offered_slots=(), reply="booked mon-9am for Ada"
            )
        ),
        "b1",
    )

    tool_turn = llm_tool_handler.begin()

    assert tool_turn.tools == ()


def test_collecting_a_name_offers_exactly_a_required_name_argument() -> None:
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


def test_choosing_a_slot_offers_exactly_the_slots_the_state_carries() -> None:
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

    tool = llm_tool_handler.begin().tools[0]

    assert tool.name == handlers.CHOOSE_SLOT
    properties = tool.parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["mon-9am", "tue-2pm"]
    assert tool.parameters["required"] == ["slot"]


def test_confirming_offers_a_tool_that_takes_no_argument() -> None:
    llm_tool_handler = handlers.LlmToolHandler(
        FakeSchedulingClientScripted(
            client.BookingStateResponse(
                step="confirm", offered_slots=("mon-9am",), reply="ask the caller to confirm"
            )
        ),
        "b1",
    )

    tool_turn = llm_tool_handler.begin()

    assert [tool.name for tool in tool_turn.tools] == [
        handlers.CHOOSE_SLOT,
        handlers.CONFIRM_BOOKING,
    ]
    assert tool_turn.tools[1].parameters == {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }


def test_a_state_the_handler_declares_no_tools_for_is_not_answered_silently() -> None:
    llm_tool_handler = handlers.LlmToolHandler(
        FakeSchedulingClientScripted(
            client.BookingStateResponse(step="cancelled", offered_slots=(), reply="done")
        ),
        "b1",
    )

    with pytest.raises(KeyError):
        llm_tool_handler.begin()


def test_the_handler_answers_the_surface_the_host_wires() -> None:
    llm_tool_handler = handlers.LlmToolHandler(
        FakeSchedulingClientScripted(
            client.BookingStateResponse(
                step="collect_name", offered_slots=(), reply="ask the caller for their name"
            )
        ),
        "b1",
    )

    surface: protocol.ToolSurface = llm_tool_handler
    tool_turn: protocol.ToolTurn = surface.begin()

    assert tool_turn.reply == "ask the caller for their name"


def test_a_rejected_transition_reaches_the_host_untranslated() -> None:
    fake_scheduling_client_scripted = FakeSchedulingClientScripted(
        error=ValueError("not available at step booked")
    )
    llm_tool_handler = handlers.LlmToolHandler(fake_scheduling_client_scripted, "b1")

    with pytest.raises(ValueError) as excinfo:
        llm_tool_handler.choose_slot(
            protocol.ToolCall(handlers.CHOOSE_SLOT, {"slot": "mon-9am"})
        )

    assert "not available at step booked" in str(excinfo.value)
    assert len(fake_scheduling_client_scripted.requests) == 1
