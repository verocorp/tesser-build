from __future__ import annotations

from typing import Final

import tesser.domain as ts


@ts.do_not_use_function
def canonical_str(value: str) -> str:
    return value

COLLECT_NAME: Final[str] = "collect_name"
CHOOSE_SLOT: Final[str] = "choose_slot"
CONFIRM: Final[str] = "confirm"
BOOKED: Final[str] = "booked"
STEPS: Final[tuple[str, ...]] = (COLLECT_NAME, CHOOSE_SLOT, CONFIRM, BOOKED)


class Step(ts.ValueObject):

    _label: str

    def __init__(self, label: str) -> None:
        if label not in STEPS:
            raise ValueError(f"unknown step {label!r}")
        object.__setattr__(self, "_label", label)

    def __str__(self) -> str:
        return canonical_str(self._label)


class CustomerName(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value.strip():
            raise ValueError("name must be non-empty")
        if len(value.strip()) > 200:
            raise ValueError("name is too long")
        object.__setattr__(self, "_value", value.strip())

    def __str__(self) -> str:
        return canonical_str(self._value)


class Slot(ts.ValueObject):

    _label: str

    def __init__(self, label: str) -> None:
        if not label.strip():
            raise ValueError("slot label must be non-empty")
        if len(label.strip()) > 100:
            raise ValueError("slot label is too long")
        object.__setattr__(self, "_label", label.strip())

    def __str__(self) -> str:
        return canonical_str(self._label)


class BookingSpec(ts.Spec):

    def __init__(
        self, step: str, name: str, chosen: str, offered: tuple[str, ...]
    ) -> None:
        self.step = step
        self.name = name
        self.chosen = chosen
        self.offered = offered


class Booking(ts.AggregateRoot):

    def __init__(self, spec: BookingSpec) -> None:
        self._step = Step(spec.step)
        self._name = CustomerName(spec.name) if spec.name else None
        self._chosen = Slot(spec.chosen) if spec.chosen else None
        self._offered = tuple(Slot(label) for label in spec.offered)
        if spec.step != COLLECT_NAME and self._name is None:
            raise ValueError(f"step {spec.step} requires a name")
        if spec.step == COLLECT_NAME and (self._name or self._chosen or self._offered):
            raise ValueError("step collect_name carries no name, slot, or offers")
        if spec.step in (CHOOSE_SLOT, CONFIRM) and not self._offered:
            raise ValueError(f"step {spec.step} requires offered slots")
        if spec.step == CHOOSE_SLOT and self._chosen is not None:
            raise ValueError("step choose_slot carries no chosen slot")
        if spec.step in (CONFIRM, BOOKED) and self._chosen is None:
            raise ValueError(f"step {spec.step} requires a chosen slot")
        if self._chosen is not None and self._chosen not in self._offered:
            raise ValueError("the chosen slot must be among the offered slots")

    def step(self) -> Step:
        return self._step

    def name(self) -> CustomerName | None:
        return self._name

    def chosen(self) -> Slot | None:
        return self._chosen

    def offered(self) -> tuple[Slot, ...]:
        return self._offered

    def provide_name(self, name: CustomerName, offered: tuple[Slot, ...]) -> None:
        self._require(COLLECT_NAME)
        if not offered:
            raise ValueError("no slots are available")
        self._name = name
        self._offered = offered
        self._step = Step(CHOOSE_SLOT)

    def choose_slot(self, slot: Slot) -> None:
        if str(self._step) not in (CHOOSE_SLOT, CONFIRM):
            raise ValueError(f"choosing a slot is not available at step {self._step}")
        if slot not in self._offered:
            offered = ", ".join(str(s) for s in self._offered)
            raise ValueError(
                f"slot {slot} is not available; available slots: {offered}"
            )
        self._chosen = slot
        self._step = Step(CONFIRM)

    def reoffer(self, offered: tuple[Slot, ...]) -> None:
        self._require(CONFIRM)
        if not offered:
            raise ValueError("no slots are available")
        self._offered = offered
        self._chosen = None
        self._step = Step(CHOOSE_SLOT)

    def confirm(self) -> None:
        self._require(CONFIRM)
        self._step = Step(BOOKED)

    def _require(self, label: str) -> None:
        if str(self._step) != label:
            raise ValueError(f"not available at step {self._step}")
