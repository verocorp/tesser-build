from __future__ import annotations

import tesser.application as ts


class BookingParts(ts.Parts):

    def __init__(
        self, step: str, name: str, chosen: str, offered: tuple[str, ...]
    ) -> None:
        self.step = step
        self.name = name
        self.chosen = chosen
        self.offered = offered


class Reserved(ts.Parts):

    def __init__(self) -> None:
        return None


class SlotTaken(ts.Parts):

    def __init__(self, available: tuple[str, ...]) -> None:
        self.available = available
