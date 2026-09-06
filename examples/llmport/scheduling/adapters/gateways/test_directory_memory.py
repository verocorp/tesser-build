from __future__ import annotations

import scheduling.adapters.gateways as gateways
import scheduling.application.ports as ports


def test_the_directory_offers_the_slots_it_was_opened_with() -> None:
    memory_slot_directory = gateways.MemorySlotDirectory(("mon-9am", "tue-2pm"))

    available_slots_response = memory_slot_directory.available(
        ports.AvailableSlotsRequest()
    )

    assert available_slots_response.slots == ("mon-9am", "tue-2pm")


def test_an_empty_directory_offers_nothing() -> None:
    memory_slot_directory = gateways.MemorySlotDirectory(())

    available_slots_response = memory_slot_directory.available(
        ports.AvailableSlotsRequest()
    )

    assert available_slots_response.slots == ()


def test_reserving_an_offered_slot_takes_it_for_the_caller() -> None:
    memory_slot_directory = gateways.MemorySlotDirectory(("mon-9am", "tue-2pm"))

    reserve_slot_response = memory_slot_directory.reserve(
        ports.ReserveSlotRequest(slot="mon-9am", name="Ada Lovelace")
    )

    assert reserve_slot_response.outcome is ports.ReservationOutcome.RESERVED
    assert reserve_slot_response.available == ()
    assert memory_slot_directory.reserved == [("mon-9am", "Ada Lovelace")]


def test_a_reserved_slot_is_no_longer_offered() -> None:
    memory_slot_directory = gateways.MemorySlotDirectory(("mon-9am", "tue-2pm"))
    memory_slot_directory.reserve(ports.ReserveSlotRequest(slot="mon-9am", name="Ada"))

    available_slots_response = memory_slot_directory.available(
        ports.AvailableSlotsRequest()
    )

    assert available_slots_response.slots == ("tue-2pm",)


def test_reserving_the_same_slot_twice_comes_back_taken_with_what_is_left() -> None:
    memory_slot_directory = gateways.MemorySlotDirectory(("mon-9am", "tue-2pm"))
    memory_slot_directory.reserve(ports.ReserveSlotRequest(slot="mon-9am", name="Ada"))

    reserve_slot_response = memory_slot_directory.reserve(
        ports.ReserveSlotRequest(slot="mon-9am", name="Grace")
    )

    assert reserve_slot_response.outcome is ports.ReservationOutcome.SLOT_TAKEN
    assert reserve_slot_response.available == ("tue-2pm",)
    assert memory_slot_directory.reserved == [("mon-9am", "Ada")]


def test_reserving_a_slot_the_directory_never_offered_comes_back_taken() -> None:
    memory_slot_directory = gateways.MemorySlotDirectory(("mon-9am",))

    reserve_slot_response = memory_slot_directory.reserve(
        ports.ReserveSlotRequest(slot="wed-4pm", name="Ada")
    )

    assert reserve_slot_response.outcome is ports.ReservationOutcome.SLOT_TAKEN
    assert reserve_slot_response.available == ("mon-9am",)
    assert memory_slot_directory.reserved == []


def test_the_last_slot_taken_leaves_nothing_to_offer() -> None:
    memory_slot_directory = gateways.MemorySlotDirectory(("mon-9am",))
    memory_slot_directory.reserve(ports.ReserveSlotRequest(slot="mon-9am", name="Ada"))

    reserve_slot_response = memory_slot_directory.reserve(
        ports.ReserveSlotRequest(slot="mon-9am", name="Grace")
    )

    assert reserve_slot_response.outcome is ports.ReservationOutcome.SLOT_TAKEN
    assert reserve_slot_response.available == ()


def test_each_reservation_records_the_caller_who_made_it() -> None:
    memory_slot_directory = gateways.MemorySlotDirectory(("mon-9am", "tue-2pm"))

    memory_slot_directory.reserve(ports.ReserveSlotRequest(slot="tue-2pm", name="Grace"))
    memory_slot_directory.reserve(ports.ReserveSlotRequest(slot="mon-9am", name="Ada"))

    assert memory_slot_directory.reserved == [("tue-2pm", "Grace"), ("mon-9am", "Ada")]
