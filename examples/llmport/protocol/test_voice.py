from __future__ import annotations

import pytest
import tesser.testing as ts

import protocol.voice as voice


@ts.fake
class FakeToolEndpoint(voice.ToolEndpoint):

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[voice.ToolCall] = []

    def __call__(self, call: voice.ToolCall, /) -> voice.ToolTurn:
        self.calls.append(call)
        return voice.ToolTurn(reply=self.reply, tools=())


def test_a_tool_renders_the_schema_the_model_is_handed() -> None:
    tool = voice.Tool("provide_name", "Record the caller's full name.", {"type": "object"})

    assert tool.schema() == {
        "name": "provide_name",
        "description": "Record the caller's full name.",
        "parameters": {"type": "object"},
    }


def test_a_tool_does_not_alias_the_parameters_it_was_handed() -> None:
    inner: dict[str, object] = {"enum": ["mon-9am"]}
    parameters: dict[str, object] = {"properties": {"slot": inner}}

    tool = voice.Tool("choose_slot", "Record the slot the caller chose.", parameters)
    parameters["properties"] = "replaced"
    inner["enum"] = ["changed"]

    assert tool.parameters == {"properties": {"slot": {"enum": ["mon-9am"]}}}


def test_a_rendered_schema_does_not_alias_the_tool_it_came_from() -> None:
    tool = voice.Tool("choose_slot", "Record the slot the caller chose.", {"properties": {}})

    rendered = tool.schema()
    parameters = rendered["parameters"]
    assert isinstance(parameters, dict)
    parameters["properties"] = "changed"

    assert tool.parameters == {"properties": {}}


def test_two_tools_declaring_the_same_thing_are_equal() -> None:
    tool = voice.Tool("provide_name", "Record the caller's full name.", {"type": "object"})

    assert tool == voice.Tool(
        "provide_name", "Record the caller's full name.", {"type": "object"}
    )
    assert tool != voice.Tool(
        "choose_slot", "Record the caller's full name.", {"type": "object"}
    )
    assert tool != voice.Tool(
        "provide_name", "Record the caller's full name.", {"type": "string"}
    )


def test_a_tool_cannot_be_rewritten_after_it_is_declared() -> None:
    tool = voice.Tool("provide_name", "Record the caller's full name.", {"type": "object"})

    with pytest.raises(AttributeError):
        tool.name = "cancel_booking"


def test_a_tool_call_reads_each_string_argument_it_carries() -> None:
    call = voice.ToolCall("provide_name", {"name": "Ada Lovelace", "slot": "mon-9am"})

    assert call.text("name") == "Ada Lovelace"
    assert call.text("slot") == "mon-9am"


def test_a_non_string_argument_is_rejected_naming_the_argument() -> None:
    call = voice.ToolCall("provide_name", {"name": 3})

    with pytest.raises(voice.BadToolCall) as excinfo:
        call.text("name")

    assert "name" in str(excinfo.value)


def test_an_absent_argument_is_rejected_naming_the_argument() -> None:
    call = voice.ToolCall("choose_slot", {})

    with pytest.raises(voice.BadToolCall) as excinfo:
        call.text("slot")

    assert "slot" in str(excinfo.value)


def test_a_bad_tool_call_is_not_confusable_with_a_domain_rejection() -> None:
    call = voice.ToolCall("provide_name", {"name": None})

    with pytest.raises(voice.BadToolCall) as excinfo:
        call.text("name")

    assert not isinstance(excinfo.value, ValueError)


def test_a_tool_call_does_not_alias_the_arguments_it_was_handed() -> None:
    nested: dict[str, object] = {"depth": 1}
    arguments: dict[str, object] = {"name": "Ada", "nested": nested}

    call = voice.ToolCall("provide_name", arguments)
    arguments["name"] = "Eve"
    nested["depth"] = 2

    assert call.arguments == {"name": "Ada", "nested": {"depth": 1}}


def test_a_turn_carries_the_reply_and_the_tools_it_offers() -> None:
    tool = voice.Tool("provide_name", "Record the caller's full name.", {"type": "object"})

    turn = voice.ToolTurn(reply="ask the caller for their name", tools=(tool,))

    assert turn.reply == "ask the caller for their name"
    assert turn.tools == (tool,)


def test_a_turn_that_offers_nothing_ends_the_tool_exchange() -> None:
    turn = voice.ToolTurn(reply="booked mon-9am for Ada", tools=())

    assert turn.tools == ()


def test_a_route_carries_the_endpoint_the_host_calls() -> None:
    endpoint = FakeToolEndpoint("offer the caller the available slots")

    route = voice.Route("provide_name", endpoint)
    turn = route.endpoint(voice.ToolCall("provide_name", {"name": "Ada"}))

    assert route.name == "provide_name"
    assert turn.reply == "offer the caller the available slots"
    assert [call.name for call in endpoint.calls] == ["provide_name"]
