from __future__ import annotations

import collections.abc as abc
import typing

import tesser.adapters as ts

import protocol
import scheduling.client as client

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
        self._scheduling_client = scheduling_client
        self._booking_id = booking_id
        self._declarations: dict[
            str,
            tuple[str, abc.Callable[[client.BookingStateResponse], dict[str, object]]],  # tesser:debt TB022
        ] = {
            PROVIDE_NAME: (
                "Record the caller's full name.",
                lambda _state: {  # tesser:debt TB023
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                    "additionalProperties": False,
                },
            ),
            CHOOSE_SLOT: (
                "Record the slot the caller chose.",
                lambda state: {  # tesser:debt TB023
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
                lambda _state: {  # tesser:debt TB023
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

    def begin(self) -> protocol.ToolTurn:
        booking_state_response = self._scheduling_client.begin(
            client.BeginBookingRequest(booking_id=self._booking_id)
        )
        tools: list[protocol.Tool] = []
        for name in TOOLS_FOR_STEP[booking_state_response.step]:
            if name not in self._declarations:
                raise ValueError(f"unknown tool {name!r}")
            description, parameters = self._declarations[name]
            tools.append(
                protocol.Tool(
                    name=name,
                    description=description,
                    parameters=parameters(booking_state_response),
                )
            )
        return protocol.ToolTurn(reply=booking_state_response.reply, tools=tuple(tools))

    def status(self) -> protocol.ToolTurn:
        booking_state_response = self._scheduling_client.status(
            client.StatusRequest(booking_id=self._booking_id)
        )
        tools: list[protocol.Tool] = []
        for name in TOOLS_FOR_STEP[booking_state_response.step]:
            if name not in self._declarations:
                raise ValueError(f"unknown tool {name!r}")
            description, parameters = self._declarations[name]
            tools.append(
                protocol.Tool(
                    name=name,
                    description=description,
                    parameters=parameters(booking_state_response),
                )
            )
        return protocol.ToolTurn(reply=booking_state_response.reply, tools=tuple(tools))

    def provide_name(self, tool_call: protocol.ToolCall, /) -> protocol.ToolTurn:
        booking_state_response = self._scheduling_client.provide_name(
            client.ProvideNameRequest(
                booking_id=self._booking_id, name=tool_call.text("name")
            )
        )
        tools: list[protocol.Tool] = []
        for name in TOOLS_FOR_STEP[booking_state_response.step]:
            if name not in self._declarations:
                raise ValueError(f"unknown tool {name!r}")
            description, parameters = self._declarations[name]
            tools.append(
                protocol.Tool(
                    name=name,
                    description=description,
                    parameters=parameters(booking_state_response),
                )
            )
        return protocol.ToolTurn(reply=booking_state_response.reply, tools=tuple(tools))

    def choose_slot(self, tool_call: protocol.ToolCall, /) -> protocol.ToolTurn:
        booking_state_response = self._scheduling_client.choose_slot(
            client.ChooseSlotRequest(
                booking_id=self._booking_id, slot=tool_call.text("slot")
            )
        )
        tools: list[protocol.Tool] = []
        for name in TOOLS_FOR_STEP[booking_state_response.step]:
            if name not in self._declarations:
                raise ValueError(f"unknown tool {name!r}")
            description, parameters = self._declarations[name]
            tools.append(
                protocol.Tool(
                    name=name,
                    description=description,
                    parameters=parameters(booking_state_response),
                )
            )
        return protocol.ToolTurn(reply=booking_state_response.reply, tools=tuple(tools))

    def confirm(self, tool_call: protocol.ToolCall, /) -> protocol.ToolTurn:
        booking_state_response = self._scheduling_client.confirm(
            client.ConfirmBookingRequest(booking_id=self._booking_id)
        )
        tools: list[protocol.Tool] = []
        for name in TOOLS_FOR_STEP[booking_state_response.step]:
            if name not in self._declarations:
                raise ValueError(f"unknown tool {name!r}")
            description, parameters = self._declarations[name]
            tools.append(
                protocol.Tool(
                    name=name,
                    description=description,
                    parameters=parameters(booking_state_response),
                )
            )
        return protocol.ToolTurn(reply=booking_state_response.reply, tools=tuple(tools))
