from __future__ import annotations

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


class MapToToolTurn(ts.Mapper, protocol.ToolTurn):

    def __init__(self, booking: client.Booking) -> None:
        tools: list[protocol.Tool] = []
        for name in TOOLS_FOR_STEP[booking.step]:
            if name == PROVIDE_NAME:
                description = "Record the caller's full name."
                parameters: dict[str, object] = {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                    "additionalProperties": False,
                }
            elif name == CHOOSE_SLOT:
                description = "Record the slot the caller chose."
                parameters = {
                    "type": "object",
                    "properties": {
                        "slot": {
                            "type": "string",
                            "enum": list(booking.offered_slots),
                        }
                    },
                    "required": ["slot"],
                    "additionalProperties": False,
                }
            elif name == CONFIRM_BOOKING:
                description = "Book the chosen slot after the caller confirms."
                parameters = {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                }
            else:
                raise ValueError(f"unknown tool {name!r}")
            tools.append(
                protocol.Tool(name=name, description=description, parameters=parameters)
            )
        super().__init__(reply=booking.reply, tools=tuple(tools))


class LlmToolHandler(ts.Handler):

    def __init__(self, scheduling_client: client.SchedulingClient, booking_id: str) -> None:
        self._scheduling_client = scheduling_client
        self._booking_id = booking_id

    def instructions(self) -> str:
        return (
            "Help the caller book an appointment."
            " Use the tools to record what they say; never invent slots."
        )

    def begin(self) -> protocol.ToolTurn:
        begin_response = self._scheduling_client.begin(
            client.BeginBookingRequest(booking_id=self._booking_id)
        )
        return MapToToolTurn(begin_response.booking)

    def status(self) -> protocol.ToolTurn:
        status_response = self._scheduling_client.status(
            client.StatusRequest(booking_id=self._booking_id)
        )
        return MapToToolTurn(status_response.booking)

    def provide_name(self, tool_call: protocol.ToolCall, /) -> protocol.ToolTurn:
        provide_name_response = self._scheduling_client.provide_name(
            client.ProvideNameRequest(
                booking_id=self._booking_id, name=tool_call.text("name")
            )
        )
        return MapToToolTurn(provide_name_response.booking)

    def choose_slot(self, tool_call: protocol.ToolCall, /) -> protocol.ToolTurn:
        choose_slot_response = self._scheduling_client.choose_slot(
            client.ChooseSlotRequest(
                booking_id=self._booking_id, slot=tool_call.text("slot")
            )
        )
        return MapToToolTurn(choose_slot_response.booking)

    def confirm(self, tool_call: protocol.ToolCall, /) -> protocol.ToolTurn:
        confirm_response = self._scheduling_client.confirm(
            client.ConfirmBookingRequest(booking_id=self._booking_id)
        )
        return MapToToolTurn(confirm_response.booking)
