from __future__ import annotations

from collections.abc import Callable, Mapping
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
        self._tools: dict[
            str,
            tuple[
                str,
                Callable[[client.BookingStateResponse], dict[str, object]],
                Callable[[Mapping[str, object]], client.BookingStateResponse],
            ],
        ] = {
            PROVIDE_NAME: (
                "Record the caller's full name.",
                lambda state: _params({"name": {"type": "string"}}, ("name",)),
                self._provide_name,
            ),
            CHOOSE_SLOT: (
                "Record the slot the caller chose.",
                lambda state: _params(
                    {"slot": {"type": "string", "enum": list(state.offered_slots)}}, ("slot",)
                ),
                self._choose_slot,
            ),
            CONFIRM_BOOKING: (
                "Book the chosen slot after the caller confirms.",
                lambda state: _params({}, ()),
                self._confirm,
            ),
        }

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
        bound = self._tools.get(tool)
        if bound is None:
            raise ValueError(f"unknown tool {tool!r}")
        return self._turn(bound[2](raw_arguments))

    def _provide_name(self, raw: Mapping[str, object]) -> client.BookingStateResponse:
        return self._client.provide_name(
            client.ProvideNameRequest(booking_id=self._booking_id, name=_text(raw, "name"))
        )

    def _choose_slot(self, raw: Mapping[str, object]) -> client.BookingStateResponse:
        return self._client.choose_slot(
            client.ChooseSlotRequest(booking_id=self._booking_id, slot=_text(raw, "slot"))
        )

    def _confirm(self, raw: Mapping[str, object]) -> client.BookingStateResponse:
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
            tools=tuple(self._tool(name, state) for name in TOOLS_FOR_STEP[state.step]),
        )

    def _tool(self, name: str, state: client.BookingStateResponse) -> voicewire.Tool:
        description, parameters, _ = self._tools[name]
        return voicewire.Tool(name=name, description=description, parameters=parameters(state))


@ts.function
def _params(properties: dict[str, object], required: tuple[str, ...]) -> dict[str, object]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


@ts.function
def _text(raw_arguments: Mapping[str, object], key: str) -> str:
    value = raw_arguments.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value
