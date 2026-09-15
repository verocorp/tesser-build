from __future__ import annotations

import enum
import uuid

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization


class CallId(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class PersonName(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class PhoneNumber(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class CallLookup(ts.Outcome):
    FOUND = enum.auto()
    NOT_FOUND = enum.auto()


class CallPresenceSpec(ts.Spec):

    def __init__(self, presence: str) -> None:
        self.presence = presence


class CallPresence(ts.ValueObject):

    _presence: str

    def __init__(self, spec: CallPresenceSpec) -> None:
        if spec.presence not in ("found", "not_found"):
            raise errors.invalid("invalid_presence", f"presence {spec.presence!r} is not a presence")
        object.__setattr__(self, "_presence", spec.presence)

    def decide(self) -> CallLookup:
        if self._presence == "found":
            return CallLookup.FOUND
        return CallLookup.NOT_FOUND


class CallSpec(ts.Spec):

    def __init__(self, person_name: str, phone_number: str) -> None:
        self.person_name = person_name
        self.phone_number = phone_number


class Call(ts.AggregateRoot):

    def __init__(self, spec: CallSpec) -> None:
        self._call_id = CallId(str(uuid.uuid4()))
        self._person_name = PersonName(spec.person_name)
        self._phone_number = PhoneNumber(spec.phone_number)

    @property
    def identity(self) -> CallId:
        return self._call_id

    @property
    def person_name(self) -> PersonName:
        return self._person_name

    @property
    def phone_number(self) -> PhoneNumber:
        return self._phone_number
