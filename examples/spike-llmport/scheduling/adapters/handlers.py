from __future__ import annotations

from collections.abc import Mapping
from typing import Final

import tesser.adapters as ts

import scheduling.client as client
import voicewire

PROVIDE_NAME: Final[str] = "provide_name"
CHOOSE_SLOT: Final[str] = "choose_slot"
CONFIRM_BOOKING: Final[str] = "confirm_booking"
TOOLS_FOR_STEP: Final[dict[str, tuple[str, ...]]] = {
    "collect_name": (PROVIDE_NAME,),
    "choose_slot": (CHOOSE_SLOT,),
    "confirm": (CHOOSE_SLOT, CONFIRM_BOOKING),
    "booked": (),
}


class LlmToolHandler(ts.Handler):

    def __init__(self, scheduling_client: client.SchedulingClient, booking_id: str) -> None:
        self._client = scheduling_client
        self._booking_id = booking_id

    def begin(self) -> voicewire.ToolTurn:
        return self._turn(self._client.begin(client.BeginBookingRequest(booking_id=self._booking_id)))

    def status(self) -> voicewire.ToolTurn:
        return self._turn(self._client.status(client.StatusRequest(booking_id=self._booking_id)))

    def instructions(self) -> str:
        return (
            "Help the caller book an appointment."
            " Use the tools to record what they say; never invent slots."
        )

    def dispatch(self, tool: str, raw_arguments: Mapping[str, object]) -> voicewire.ToolTurn:
        if tool == PROVIDE_NAME:
            return self._turn(
                self._client.provide_name(
                    client.ProvideNameRequest(
                        booking_id=self._booking_id, name=_text(raw_arguments, "name")
                    )
                )
            )
        if tool == CHOOSE_SLOT:
            return self._turn(
                self._client.choose_slot(
                    client.ChooseSlotRequest(
                        booking_id=self._booking_id, slot=_text(raw_arguments, "slot")
                    )
                )
            )
        if tool == CONFIRM_BOOKING:
            return self._turn(self._confirm())
        raise ValueError(f"unknown tool {tool!r}")

    def _confirm(self) -> client.BookingStateResponse:
        try:
            return self._client.confirm(
                client.ConfirmBookingRequest(booking_id=self._booking_id)
            )
        except ValueError as err:
            state = self._client.status(client.StatusRequest(booking_id=self._booking_id))
            if state.step != "confirm":
                raise
            try:
                fresh = self._client.reoffer(
                    client.ReofferRequest(booking_id=self._booking_id)
                )
            except ValueError as exhausted:
                raise ValueError(f"{err}; {exhausted}") from err
            offered = ", ".join(fresh.offered_slots)
            raise ValueError(f"{err}; now available: {offered}") from err

    def _turn(self, state: client.BookingStateResponse) -> voicewire.ToolTurn:
        return voicewire.ToolTurn(
            reply=state.reply,
            tools=tuple(self._schema(tool, state) for tool in TOOLS_FOR_STEP[state.step]),
        )

    def _schema(self, tool: str, state: client.BookingStateResponse) -> dict[str, object]:
        if tool == PROVIDE_NAME:
            return {
                "name": tool,
                "description": "Record the caller's full name.",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                    "additionalProperties": False,
                },
            }
        if tool == CHOOSE_SLOT:
            return {
                "name": tool,
                "description": "Record the slot the caller chose.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slot": {"type": "string", "enum": list(state.offered_slots)}
                    },
                    "required": ["slot"],
                    "additionalProperties": False,
                },
            }
        if tool == CONFIRM_BOOKING:
            return {
                "name": tool,
                "description": "Book the chosen slot after the caller confirms.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            }
        raise ValueError(f"unknown tool {tool!r}")


@ts.function
def _text(raw_arguments: Mapping[str, object], key: str) -> str:
    value = raw_arguments.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value
