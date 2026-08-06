from __future__ import annotations

import enum

import tesser.domain as ts


class DomainKind(enum.Enum):

    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"


class DomainError(Exception):

    def __init__(self, kind: DomainKind, code: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.code = code
        self.message = message

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class InfraError(Exception):
    pass


class Step(enum.Enum):

    COLLECT_NAME = "collect_name"
    CHOOSE_SLOT = "choose_slot"
    CONFIRM = "confirm"
    BOOKED = "booked"


class CustomerName(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value.strip():
            raise DomainError(
                DomainKind.VALIDATION, "empty_name", "name must be non-empty"
            )
        object.__setattr__(self, "_value", value.strip())

    def __str__(self) -> str:
        return self._value


class Slot(ts.ValueObject):

    _label: str

    def __init__(self, label: str) -> None:
        if not label.strip():
            raise DomainError(
                DomainKind.VALIDATION, "empty_slot", "slot label must be non-empty"
            )
        object.__setattr__(self, "_label", label.strip())

    def __str__(self) -> str:
        return self._label


class ProvideName(ts.ValueObject):

    _name: CustomerName

    def __init__(self, name: CustomerName) -> None:
        object.__setattr__(self, "_name", name)

    def name(self) -> CustomerName:
        return self._name


class ChooseSlot(ts.ValueObject):

    _slot: Slot

    def __init__(self, slot: Slot) -> None:
        object.__setattr__(self, "_slot", slot)

    def slot(self) -> Slot:
        return self._slot


class ConfirmBooking(ts.ValueObject):
    pass


Command = ProvideName | ChooseSlot | ConfirmBooking


class BookingSpec(ts.Spec):
    pass


class Booking(ts.AggregateRoot):

    def __init__(self, spec: BookingSpec) -> None:
        self._step = Step.COLLECT_NAME
        self._name: CustomerName | None = None
        self._offered: tuple[Slot, ...] = ()
        self._chosen: Slot | None = None

    def step(self) -> Step:
        return self._step

    def offered_slots(self) -> tuple[Slot, ...]:
        return self._offered

    def customer_name(self) -> CustomerName:
        if self._name is None:
            raise DomainError(
                DomainKind.VALIDATION, "no_name", "no name has been provided"
            )
        return self._name

    def chosen_slot(self) -> Slot:
        if self._chosen is None:
            raise DomainError(
                DomainKind.VALIDATION, "no_slot", "no slot has been chosen"
            )
        return self._chosen

    def provide_name(self, name: CustomerName, offered: tuple[Slot, ...]) -> None:
        self._require(Step.COLLECT_NAME)
        if not offered:
            raise DomainError(DomainKind.NOT_FOUND, "no_slots", "no slots are available")
        self._name = name
        self._offered = offered
        self._step = Step.CHOOSE_SLOT

    def choose_slot(self, slot: Slot) -> None:
        if self._step not in (Step.CHOOSE_SLOT, Step.CONFIRM):
            self._require(Step.CHOOSE_SLOT)
        if slot not in self._offered:
            offered = ", ".join(str(s) for s in self._offered)
            raise DomainError(
                DomainKind.VALIDATION,
                "slot_not_offered",
                f"slot {slot} is not available; available slots: {offered}",
            )
        self._chosen = slot
        self._step = Step.CONFIRM

    def reoffer(self, offered: tuple[Slot, ...]) -> None:
        self._require(Step.CONFIRM)
        if not offered:
            raise DomainError(DomainKind.NOT_FOUND, "no_slots", "no slots are available")
        self._offered = offered
        self._chosen = None
        self._step = Step.CHOOSE_SLOT

    def confirm(self) -> None:
        self._require(Step.CONFIRM)
        self._step = Step.BOOKED

    def _require(self, step: Step) -> None:
        if self._step is not step:
            raise DomainError(
                DomainKind.VALIDATION,
                "wrong_step",
                f"not available at step {self._step.value}",
            )
