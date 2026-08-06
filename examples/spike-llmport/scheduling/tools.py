from __future__ import annotations

import enum
from collections.abc import Mapping
from typing import assert_never

import tesser.application as ts

from scheduling.domain import (
    Booking,
    ChooseSlot,
    Command,
    ConfirmBooking,
    CustomerName,
    DomainError,
    DomainKind,
    ProvideName,
    Slot,
    Step,
)


class ToolName(enum.Enum):

    PROVIDE_NAME = "provide_name"
    CHOOSE_SLOT = "choose_slot"
    CONFIRM_BOOKING = "confirm_booking"


@ts.function
def allowed_tools(step: Step) -> tuple[ToolName, ...]:
    match step:
        case Step.COLLECT_NAME:
            return (ToolName.PROVIDE_NAME,)
        case Step.CHOOSE_SLOT:
            return (ToolName.CHOOSE_SLOT,)
        case Step.CONFIRM:
            return (ToolName.CHOOSE_SLOT, ToolName.CONFIRM_BOOKING)
        case Step.BOOKED:
            return ()
    assert_never(step)


@ts.function
def schema_for(name: ToolName, booking: Booking) -> dict[str, object]:
    match name:
        case ToolName.PROVIDE_NAME:
            return {
                "name": name.value,
                "description": "Record the caller's full name.",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                    "additionalProperties": False,
                },
            }
        case ToolName.CHOOSE_SLOT:
            return {
                "name": name.value,
                "description": "Record the slot the caller chose.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "slot": {
                            "type": "string",
                            "enum": [str(s) for s in booking.offered_slots()],
                        }
                    },
                    "required": ["slot"],
                    "additionalProperties": False,
                },
            }
        case ToolName.CONFIRM_BOOKING:
            return {
                "name": name.value,
                "description": "Book the chosen slot after the caller confirms.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": False,
                },
            }
    assert_never(name)


@ts.function
def parse(name: ToolName, raw_arguments: Mapping[str, object]) -> Command:
    match name:
        case ToolName.PROVIDE_NAME:
            return ProvideName(CustomerName(_required_str(raw_arguments, "name")))
        case ToolName.CHOOSE_SLOT:
            return ChooseSlot(Slot(_required_str(raw_arguments, "slot")))
        case ToolName.CONFIRM_BOOKING:
            return ConfirmBooking()
    assert_never(name)


@ts.function
def _required_str(raw_arguments: Mapping[str, object], key: str) -> str:
    value = raw_arguments.get(key)
    if not isinstance(value, str):
        raise DomainError(
            DomainKind.VALIDATION, "bad_argument", f"{key} must be a string"
        )
    return value
