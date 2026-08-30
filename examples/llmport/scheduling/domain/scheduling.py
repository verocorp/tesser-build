from __future__ import annotations

import enum
import typing

import tesser.domain as ts
import tesser.serialization as serialization

COLLECT_NAME: typing.Final[str] = "collect_name"
CHOOSE_SLOT: typing.Final[str] = "choose_slot"
CONFIRM: typing.Final[str] = "confirm"
BOOKED: typing.Final[str] = "booked"
STEPS: typing.Final[tuple[str, ...]] = (COLLECT_NAME, CHOOSE_SLOT, CONFIRM, BOOKED)


class Step(ts.ValueObject):

    _label: str

    def __init__(self, label: str) -> None:
        if label not in STEPS:
            raise ValueError(f"unknown step {label!r}")
        object.__setattr__(self, "_label", label)

    def __str__(self) -> str:
        return serialization.canonical_str(self._label)


class CustomerName(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value.strip():
            raise ValueError("name must be non-empty")
        if len(value.strip()) > 200:
            raise ValueError("name is too long")
        object.__setattr__(self, "_value", value.strip())

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Slot(ts.ValueObject):

    _label: str

    def __init__(self, label: str) -> None:
        if not label.strip():
            raise ValueError("slot label must be non-empty")
        if len(label.strip()) > 100:
            raise ValueError("slot label is too long")
        object.__setattr__(self, "_label", label.strip())

    def __str__(self) -> str:
        return serialization.canonical_str(self._label)


class BookingID(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value:
            raise ValueError("booking id must be non-empty")
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Resumed(ts.Outcome):
    RESUMED = enum.auto()
    STARTED = enum.auto()


class ResumptionSpec(ts.Spec):

    def __init__(self, presence: str) -> None:
        self.presence = presence


class Resumption(ts.ValueObject):

    _presence: str

    def __init__(self, spec: ResumptionSpec) -> None:
        if spec.presence not in ("present", "absent"):
            raise ValueError(f"presence {spec.presence!r} is not a presence")
        object.__setattr__(self, "_presence", spec.presence)

    def resumed(self) -> Resumed:
        if self._presence == "present":
            return Resumed.RESUMED
        return Resumed.STARTED


class Settled(ts.Outcome):
    BOOKED = enum.auto()
    REOFFERED = enum.auto()


class OfferSpec(ts.Spec):

    def __init__(self, labels: tuple[str, ...]) -> None:
        self.labels = labels


class Offer(ts.ValueObject):

    _slots: tuple[Slot, ...]

    def __init__(self, spec: OfferSpec) -> None:
        if not spec.labels:
            raise ValueError("no slots are available")
        object.__setattr__(self, "_slots", tuple(Slot(label) for label in spec.labels))

    @property
    def slots(self) -> tuple[Slot, ...]:
        return self._slots


class NamingSpec(ts.Spec):

    def __init__(self, name: str, offered: OfferSpec) -> None:
        self.name = name
        self.offered = offered


class Naming(ts.ValueObject):

    _name: CustomerName
    _offer: Offer

    def __init__(self, spec: NamingSpec) -> None:
        object.__setattr__(self, "_name", CustomerName(spec.name))
        object.__setattr__(self, "_offer", Offer(spec.offered))

    @property
    def name(self) -> CustomerName:
        return self._name

    @property
    def offer(self) -> Offer:
        return self._offer


class ReoffersSpec(ts.Spec):

    def __init__(self, offered: tuple[tuple[str, ...], ...]) -> None:
        self.offered = offered


class Reoffers(ts.ValueObject):

    _offered: tuple[tuple[Slot, ...], ...]

    def __init__(self, spec: ReoffersSpec) -> None:
        object.__setattr__(
            self,
            "_offered",
            tuple(tuple(Slot(label) for label in each) for each in spec.offered),
        )

    @property
    def offered(self) -> tuple[tuple[Slot, ...], ...]:
        return self._offered


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

    def provide_name(self, spec: NamingSpec) -> None:
        if str(self._step) != COLLECT_NAME:
            raise ValueError(f"not available at step {self._step}")
        naming = Naming(spec)
        self._name = naming.name
        self._offered = naming.offer.slots
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

    def reoffer(self, spec: OfferSpec) -> None:
        if str(self._step) != CONFIRM:
            raise ValueError(f"not available at step {self._step}")
        offer = Offer(spec)
        self._offered = offer.slots
        self._chosen = None
        self._step = Step(CHOOSE_SLOT)

    def confirm(self) -> None:
        if str(self._step) != CONFIRM:
            raise ValueError(f"not available at step {self._step}")
        self._step = Step(BOOKED)

    def settle(self, reoffers: Reoffers) -> Settled:
        if str(self._step) != BOOKED:
            raise ValueError(f"not available at step {self._step}")
        for offered in reoffers.offered:
            if not offered:
                raise ValueError("no slots are available")
            self._offered = offered
            self._chosen = None
            self._step = Step(CHOOSE_SLOT)
            return Settled.REOFFERED
        return Settled.BOOKED
