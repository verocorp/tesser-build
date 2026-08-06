import pytest

from scheduling.domain import (
    Booking,
    BookingSpec,
    ChooseSlot,
    ConfirmBooking,
    CustomerName,
    DomainError,
    DomainKind,
    ProvideName,
    Slot,
    Step,
)
from scheduling.tools import ToolName, allowed_tools, parse, schema_for


def test_allowed_tools_is_total_over_steps() -> None:
    for step in Step:
        assert isinstance(allowed_tools(step), tuple)


def test_every_tool_name_has_a_schema() -> None:
    booking = Booking(BookingSpec())
    booking.provide_name(CustomerName("Ada"), (Slot("mon-9am"),))
    for name in ToolName:
        schema = schema_for(name, booking)
        assert schema["name"] == name.value


def test_the_choose_slot_schema_offers_exactly_the_current_slots() -> None:
    booking = Booking(BookingSpec())
    booking.provide_name(CustomerName("Ada"), (Slot("mon-9am"), Slot("tue-2pm")))

    schema = schema_for(ToolName.CHOOSE_SLOT, booking)

    parameters = schema["parameters"]
    assert isinstance(parameters, dict)
    properties = parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["mon-9am", "tue-2pm"]


def test_the_schema_rebinds_after_the_offered_slots_change() -> None:
    booking = Booking(BookingSpec())
    booking.provide_name(CustomerName("Ada"), (Slot("mon-9am"), Slot("tue-2pm")))
    booking.choose_slot(Slot("mon-9am"))
    booking.reoffer((Slot("tue-2pm"),))

    schema = schema_for(ToolName.CHOOSE_SLOT, booking)

    parameters = schema["parameters"]
    assert isinstance(parameters, dict)
    properties = parameters["properties"]
    assert isinstance(properties, dict)
    slot = properties["slot"]
    assert isinstance(slot, dict)
    assert slot["enum"] == ["tue-2pm"]


def test_parse_builds_typed_commands() -> None:
    assert parse(ToolName.PROVIDE_NAME, {"name": "Ada"}) == ProvideName(
        CustomerName("Ada")
    )
    assert parse(ToolName.CHOOSE_SLOT, {"slot": "mon-9am"}) == ChooseSlot(
        Slot("mon-9am")
    )
    assert parse(ToolName.CONFIRM_BOOKING, {}) == ConfirmBooking()


def test_parse_rejects_a_missing_argument() -> None:
    with pytest.raises(DomainError) as excinfo:
        parse(ToolName.PROVIDE_NAME, {})
    assert excinfo.value.kind is DomainKind.VALIDATION


def test_parse_rejects_a_non_string_argument() -> None:
    with pytest.raises(DomainError) as excinfo:
        parse(ToolName.CHOOSE_SLOT, {"slot": 3})
    assert excinfo.value.kind is DomainKind.VALIDATION
