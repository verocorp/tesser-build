from __future__ import annotations

import typing

import tesser.domain as ts

import tesser.serialization as serialization

AGENT: typing.Final[str] = "agent"
PERSON: typing.Final[str] = "person"
SPEAKERS: typing.Final[tuple[str, ...]] = (AGENT, PERSON)


class Speaker(ts.ValueObject):

    _label: str

    def __init__(self, label: str) -> None:
        if label not in SPEAKERS:
            raise ValueError(f"a speaker on a call is the agent or the person, not {label!r}")
        object.__setattr__(self, "_label", label)

    def __str__(self) -> str:
        return serialization.canonical_str(self._label)


class Utterance(ts.ValueObject):

    _text: str

    def __init__(self, text: str) -> None:
        if not text.strip():
            raise ValueError("an utterance says something")
        object.__setattr__(self, "_text", text.strip())

    def __str__(self) -> str:
        return serialization.canonical_str(self._text)


class TurnSpec(ts.Spec):

    def __init__(self, speaker: str, text: str) -> None:
        self.speaker = speaker
        self.text = text


class Turn(ts.ValueObject):

    _speaker: Speaker
    _utterance: Utterance

    def __init__(self, spec: TurnSpec) -> None:
        object.__setattr__(self, "_speaker", Speaker(spec.speaker))
        object.__setattr__(self, "_utterance", Utterance(spec.text))

    @property
    def speaker(self) -> Speaker:
        return self._speaker

    @property
    def utterance(self) -> Utterance:
        return self._utterance


class ConversationSpec(ts.Spec):

    def __init__(self, turns: tuple[TurnSpec, ...]) -> None:
        self.turns = turns


class Conversation(ts.ValueObject):

    _turns: tuple[Turn, ...]

    def __init__(self, spec: ConversationSpec) -> None:
        object.__setattr__(self, "_turns", tuple(Turn(turn_spec) for turn_spec in spec.turns))

    @property
    def turns(self) -> tuple[Turn, ...]:
        return self._turns

    def with_turn(self, turn_spec: TurnSpec) -> Conversation:
        return Conversation(
            ConversationSpec(
                turns=(
                    *(TurnSpec(speaker=str(turn.speaker), text=str(turn.utterance)) for turn in self._turns),
                    turn_spec,
                )
            )
        )
