from __future__ import annotations

from collections.abc import Mapping
from typing import Final

import tesser.adapters as ts

import scheduling.client as client

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

    def begin(self) -> client.BookingStateResponse:
        return self._client.begin(client.BeginBookingRequest(booking_id=self._booking_id))

    def status(self) -> client.BookingStateResponse:
        return self._client.status(client.StatusRequest(booking_id=self._booking_id))

    def tools(self, state: client.BookingStateResponse) -> tuple[dict[str, object], ...]:
        return tuple(self._schema(tool, state) for tool in TOOLS_FOR_STEP[state.step])

    def dispatch(
        self, tool: str, raw_arguments: Mapping[str, object]
    ) -> client.BookingStateResponse:
        if tool == PROVIDE_NAME:
            return self._client.provide_name(
                client.ProvideNameRequest(
                    booking_id=self._booking_id, name=_text(raw_arguments, "name")
                )
            )
        if tool == CHOOSE_SLOT:
            return self._client.choose_slot(
                client.ChooseSlotRequest(
                    booking_id=self._booking_id, slot=_text(raw_arguments, "slot")
                )
            )
        if tool == CONFIRM_BOOKING:
            return self._confirm()
        raise ValueError(f"unknown tool {tool!r}")

    def _confirm(self) -> client.BookingStateResponse:
        try:
            return self._client.confirm(
                client.ConfirmBookingRequest(booking_id=self._booking_id)
            )
        except ValueError as err:
            state = self._client.reoffer(client.ReofferRequest(booking_id=self._booking_id))
            offered = ", ".join(state.offered_slots)
            raise ValueError(f"{err}; now available: {offered}") from err

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
        return {
            "name": tool,
            "description": "Book the chosen slot after the caller confirms.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        }


@ts.function
def _text(raw_arguments: Mapping[str, object], key: str) -> str:
    value = raw_arguments.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value
