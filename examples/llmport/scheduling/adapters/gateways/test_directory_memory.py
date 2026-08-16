from __future__ import annotations

import scheduling.adapters.gateways.directory_memory as directory_memory
import scheduling.application.ports.slot_directory as slot_directory


def test_the_directory_offers_the_slots_it_was_opened_with() -> None:
    directory = directory_memory.MemorySlotDirectory(("mon-9am", "tue-2pm"))

    available = directory.available(slot_directory.AvailableSlotsRequest())

    assert available.slots == ("mon-9am", "tue-2pm")


def test_an_empty_directory_offers_nothing() -> None:
    directory = directory_memory.MemorySlotDirectory(())

    available = directory.available(slot_directory.AvailableSlotsRequest())

    assert available.slots == ()


def test_reserving_an_offered_slot_takes_it_for_the_caller() -> None:
    directory = directory_memory.MemorySlotDirectory(("mon-9am", "tue-2pm"))

    reserved = directory.reserve(
        slot_directory.ReserveSlotRequest(slot="mon-9am", name="Ada Lovelace")
    )

    assert reserved.outcome is slot_directory.ReservationOutcome.RESERVED
    assert reserved.available == ()
    assert directory.reserved == [("mon-9am", "Ada Lovelace")]


def test_a_reserved_slot_is_no_longer_offered() -> None:
    directory = directory_memory.MemorySlotDirectory(("mon-9am", "tue-2pm"))
    directory.reserve(slot_directory.ReserveSlotRequest(slot="mon-9am", name="Ada"))

    available = directory.available(slot_directory.AvailableSlotsRequest())

    assert available.slots == ("tue-2pm",)


def test_reserving_the_same_slot_twice_comes_back_taken_with_what_is_left() -> None:
    directory = directory_memory.MemorySlotDirectory(("mon-9am", "tue-2pm"))
    directory.reserve(slot_directory.ReserveSlotRequest(slot="mon-9am", name="Ada"))

    second = directory.reserve(
        slot_directory.ReserveSlotRequest(slot="mon-9am", name="Grace")
    )

    assert second.outcome is slot_directory.ReservationOutcome.SLOT_TAKEN
    assert second.available == ("tue-2pm",)
    assert directory.reserved == [("mon-9am", "Ada")]


def test_reserving_a_slot_the_directory_never_offered_comes_back_taken() -> None:
    directory = directory_memory.MemorySlotDirectory(("mon-9am",))

    reserved = directory.reserve(
        slot_directory.ReserveSlotRequest(slot="wed-4pm", name="Ada")
    )

    assert reserved.outcome is slot_directory.ReservationOutcome.SLOT_TAKEN
    assert reserved.available == ("mon-9am",)
    assert directory.reserved == []


def test_the_last_slot_taken_leaves_nothing_to_offer() -> None:
    directory = directory_memory.MemorySlotDirectory(("mon-9am",))
    directory.reserve(slot_directory.ReserveSlotRequest(slot="mon-9am", name="Ada"))

    taken = directory.reserve(slot_directory.ReserveSlotRequest(slot="mon-9am", name="Grace"))

    assert taken.outcome is slot_directory.ReservationOutcome.SLOT_TAKEN
    assert taken.available == ()


def test_each_reservation_records_the_caller_who_made_it() -> None:
    directory = directory_memory.MemorySlotDirectory(("mon-9am", "tue-2pm"))

    directory.reserve(slot_directory.ReserveSlotRequest(slot="tue-2pm", name="Grace"))
    directory.reserve(slot_directory.ReserveSlotRequest(slot="mon-9am", name="Ada"))

    assert directory.reserved == [("tue-2pm", "Grace"), ("mon-9am", "Ada")]
