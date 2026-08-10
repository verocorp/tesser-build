from __future__ import annotations

import tesser.adapters as ts

import scheduling.application.parts as parts


class MemorySlotDirectory(ts.Gateway):
    """The in-memory slot directory — a real adapter, not a test double.

    The spike has no external calendar, so memory IS the production
    implementation, the same standing as python-app's repo_memory. It used to
    exist only as a @ts.fake declared byte-identically in two test modules;
    promoting it here gives it one home and lets integration tests wire the
    real thing (the ladder: integration fakes nothing).
    """

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
