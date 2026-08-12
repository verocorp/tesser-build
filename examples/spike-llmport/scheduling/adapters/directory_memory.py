from __future__ import annotations

import tesser.adapters as ts

import scheduling.application.parts as parts


class MemorySlotDirectory(ts.Gateway):
    def __init__(self, slots: tuple[str, ...]) -> None:
        self.slots = list(slots)
        self.reserved: list[tuple[str, str]] = []

    def available(self) -> tuple[str, ...]:
        return tuple(self.slots)

    def reserve(self, slot: str, name: str) -> parts.Reserved | parts.SlotTaken:
        if slot not in self.slots:
            return parts.SlotTaken(available=tuple(self.slots))
        self.slots.remove(slot)
        self.reserved.append((slot, name))
        return parts.Reserved()
