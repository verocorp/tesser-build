from __future__ import annotations

import enum

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


class PersonPhoneNumber(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class PersonSpec(ts.Spec):

    def __init__(self, name: str, phone_number: str) -> None:
        self.name = name
        self.phone_number = phone_number


class Person(ts.ValueObject):

    _name: PersonName
    _phone_number: PersonPhoneNumber

    def __init__(self, spec: PersonSpec) -> None:
        object.__setattr__(self, "_name", PersonName(spec.name))
        object.__setattr__(self, "_phone_number", PersonPhoneNumber(spec.phone_number))

    @property
    def name(self) -> PersonName:
        return self._name

    @property
    def phone_number(self) -> PersonPhoneNumber:
        return self._phone_number


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

    def __init__(self, call_id: str, person: PersonSpec) -> None:
        self.call_id = call_id
        self.person = person


class Call(ts.AggregateRoot):

    def __init__(self, spec: CallSpec) -> None:
        self._call_id = CallId(spec.call_id)
        self._person = Person(spec.person)

    @property
    def identity(self) -> CallId:
        return self._call_id

    @property
    def person(self) -> Person:
        return self._person
