from __future__ import annotations

import enum
import typing

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization

_QUESTION: typing.Final[str] = "Hello. Please tell me your first name."
_GREETING: typing.Final[str] = "Nice to meet you, {name}. Goodbye."
_PUNCTUATION: typing.Final[str] = " \t\r\n.,!?;:\"'"


class CallId(ts.ValueObject):
    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value)

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class PersonName(ts.ValueObject):
    _value: str

    def __init__(self, value: str) -> None:
        object.__setattr__(self, "_value", value.strip(_PUNCTUATION))

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


class Utterance(ts.ValueObject):
    _text: str

    def __init__(self, text: str) -> None:
        if not text.strip():
            raise ValueError("an utterance says something")
        object.__setattr__(self, "_text", text.strip())

    def __str__(self) -> str:
        return serialization.canonical_str(self._text)


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
    def __init__(self, call_id: str, person_name: str) -> None:
        self.call_id = call_id
        self.person_name = person_name


class Call(ts.AggregateRoot):
    def __init__(self, spec: CallSpec) -> None:
        self._call_id = CallId(spec.call_id)
        self._person_name = PersonName(spec.person_name)

    @property
    def identity(self) -> CallId:
        return self._call_id

    @property
    def person_name(self) -> PersonName:
        return self._person_name

    @property
    def question(self) -> Utterance:
        return Utterance(_QUESTION)

    @property
    def greeting(self) -> Utterance:
        return Utterance(_GREETING.format(name=str(self._person_name)))

    def person_said(self, utterance: Utterance) -> None:
        person_name = PersonName(str(utterance))
        if not str(person_name):
            raise ValueError("a name says something besides punctuation")
        self._person_name = person_name
