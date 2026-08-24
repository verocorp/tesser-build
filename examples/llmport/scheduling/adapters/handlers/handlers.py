from __future__ import annotations

import collections.abc as abc
import typing

import tesser.adapters as ts

import scheduling.client.client as client
import protocol.voice as voice

PROVIDE_NAME: typing.Final[str] = "provide_name"
CHOOSE_SLOT: typing.Final[str] = "choose_slot"
CONFIRM_BOOKING: typing.Final[str] = "confirm_booking"
TOOLS_FOR_STEP: typing.Final[dict[str, tuple[str, ...]]] = {
    "collect_name": (PROVIDE_NAME,),
    "choose_slot": (CHOOSE_SLOT,),
    "confirm": (CHOOSE_SLOT, CONFIRM_BOOKING),
    "booked": (),
}


class LlmToolHandler(ts.Handler):

    def __init__(self, scheduling_client: client.SchedulingClient, booking_id: str) -> None:
        self._client = scheduling_client
        self._booking_id = booking_id
        self._declarations: dict[
            str,
            tuple[str, abc.Callable[[client.BookingStateResponse], dict[str, object]]],
        ] = {
            PROVIDE_NAME: (
                "Record the caller's full name.",
                lambda _state: {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                    "additionalProperties": False,
                },
            ),
            CHOOSE_SLOT: (
                "Record the slot the caller chose.",
                lambda state: {
                    "type": "object",
                    "properties": {
                        "slot": {"type": "string", "enum": list(state.offered_slots)}
                    },
                    "required": ["slot"],
                    "additionalProperties": False,
                },
            ),
            CONFIRM_BOOKING: (
                "Book the chosen slot after the caller confirms.",
                lambda _state: {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            ),
        }

    def instructions(self) -> str:
        return (
            "Help the caller book an appointment."
            " Use the tools to record what they say; never invent slots."
        )

    def begin(self) -> voice.ToolTurn:
        state = self._client.begin(client.BeginBookingRequest(booking_id=self._booking_id))
        tools: list[voice.Tool] = []
        for name in TOOLS_FOR_STEP[state.step]:
            if name not in self._declarations:
                raise ValueError(f"unknown tool {name!r}")
            description, parameters = self._declarations[name]
            tools.append(
                voice.Tool(name=name, description=description, parameters=parameters(state))
            )
        return voice.ToolTurn(reply=state.reply, tools=tuple(tools))

    def status(self) -> voice.ToolTurn:
        state = self._client.status(client.StatusRequest(booking_id=self._booking_id))
        tools: list[voice.Tool] = []
        for name in TOOLS_FOR_STEP[state.step]:
            if name not in self._declarations:
                raise ValueError(f"unknown tool {name!r}")
            description, parameters = self._declarations[name]
            tools.append(
                voice.Tool(name=name, description=description, parameters=parameters(state))
            )
        return voice.ToolTurn(reply=state.reply, tools=tuple(tools))

    def provide_name(self, call: voice.ToolCall, /) -> voice.ToolTurn:
        state = self._client.provide_name(
            client.ProvideNameRequest(booking_id=self._booking_id, name=call.text("name"))
        )
        tools: list[voice.Tool] = []
        for name in TOOLS_FOR_STEP[state.step]:
            if name not in self._declarations:
                raise ValueError(f"unknown tool {name!r}")
            description, parameters = self._declarations[name]
            tools.append(
                voice.Tool(name=name, description=description, parameters=parameters(state))
            )
        return voice.ToolTurn(reply=state.reply, tools=tuple(tools))

    def choose_slot(self, call: voice.ToolCall, /) -> voice.ToolTurn:
        state = self._client.choose_slot(
            client.ChooseSlotRequest(booking_id=self._booking_id, slot=call.text("slot"))
        )
        tools: list[voice.Tool] = []
        for name in TOOLS_FOR_STEP[state.step]:
            if name not in self._declarations:
                raise ValueError(f"unknown tool {name!r}")
            description, parameters = self._declarations[name]
            tools.append(
                voice.Tool(name=name, description=description, parameters=parameters(state))
            )
        return voice.ToolTurn(reply=state.reply, tools=tuple(tools))

    def confirm(self, _call: voice.ToolCall, /) -> voice.ToolTurn:
        state = self._client.confirm(client.ConfirmBookingRequest(booking_id=self._booking_id))
        tools: list[voice.Tool] = []
        for name in TOOLS_FOR_STEP[state.step]:
            if name not in self._declarations:
                raise ValueError(f"unknown tool {name!r}")
            description, parameters = self._declarations[name]
            tools.append(
                voice.Tool(name=name, description=description, parameters=parameters(state))
            )
        return voice.ToolTurn(reply=state.reply, tools=tuple(tools))

