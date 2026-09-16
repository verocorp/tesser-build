from __future__ import annotations

import enum
import typing

import tesser.domain as ts

import tesser.errors as errors
import tesser.serialization as serialization

AGENT: typing.Final[str] = "agent"
PERSON: typing.Final[str] = "person"
SPEAKERS: typing.Final[tuple[str, ...]] = (AGENT, PERSON)
ASK_NAME: typing.Final[str] = "ask_name"
DONE: typing.Final[str] = "done"
STEPS: typing.Final[tuple[str, ...]] = (ASK_NAME, DONE)
UTTERANCE: typing.Final[str] = "utterance"
SILENCE: typing.Final[str] = "silence"
HEARD: typing.Final[tuple[str, ...]] = (UTTERANCE, SILENCE)
_PERSONA: typing.Final[str] = (
    "You are a warm, brief receptionist placing a phone call. You speak in short, natural sentences."
)
_INSTRUCTIONS: typing.Final[dict[str, str]] = {
    ASK_NAME: (
        "Greet the person and ask for their name. Once they have given it, call person_gave_name with the "
        "name exactly as they said it, then greet them by that name and say goodbye. If they have not given "
        "a name yet, ask again briefly."
    ),
    DONE: "The call is over. Say nothing.",
}


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


class Persona(ts.ValueObject):

    _value: str

    def __init__(self, value: str) -> None:
        if not value.strip():
            raise ValueError("a persona says who the agent is on the call")
        object.__setattr__(self, "_value", value.strip())

    def __str__(self) -> str:
        return serialization.canonical_str(self._value)


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

    def __init__(self, speaker: str, utterances: tuple[str, ...]) -> None:
        self.speaker = speaker
        self.utterances = utterances


class Turn(ts.ValueObject):

    _speaker: Speaker
    _utterances: tuple[Utterance, ...]

    def __init__(self, spec: TurnSpec) -> None:
        if not spec.utterances:
            raise ValueError("a turn says something")
        object.__setattr__(self, "_speaker", Speaker(spec.speaker))
        object.__setattr__(self, "_utterances", tuple(Utterance(text) for text in spec.utterances))

    @property
    def speaker(self) -> Speaker:
        return self._speaker

    @property
    def utterances(self) -> tuple[Utterance, ...]:
        return self._utterances


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
                    *(
                        TurnSpec(speaker=str(turn.speaker), utterances=tuple(str(u) for u in turn.utterances))
                        for turn in self._turns
                    ),
                    turn_spec,
                )
            )
        )

    def with_utterance(self, text: str) -> Conversation:
        if not self._turns:
            raise ValueError("an utterance extends a turn, and this conversation has none")
        last = self._turns[-1]
        return Conversation(
            ConversationSpec(
                turns=(
                    *(
                        TurnSpec(speaker=str(turn.speaker), utterances=tuple(str(u) for u in turn.utterances))
                        for turn in self._turns[:-1]
                    ),
                    TurnSpec(speaker=str(last.speaker), utterances=(*(str(u) for u in last.utterances), text)),
                )
            )
        )


class CallStep(ts.ValueObject):

    _label: str

    def __init__(self, label: str) -> None:
        if label not in STEPS:
            raise errors.invalid("invalid_step", f"a call has no step {label!r}")
        object.__setattr__(self, "_label", label)

    def __str__(self) -> str:
        return serialization.canonical_str(self._label)


class Instructions(ts.ValueObject):

    _text: str

    def __init__(self, text: str) -> None:
        object.__setattr__(self, "_text", text)

    def __str__(self) -> str:
        return serialization.canonical_str(self._text)


class AgentTurnSpec(ts.Spec):

    def __init__(self, text: str, person_names: tuple[str, ...]) -> None:
        self.text = text
        self.person_names = person_names


class AgentTurn(ts.ValueObject):

    _utterances: tuple[Utterance, ...]
    _person_names: tuple[PersonName, ...]

    def __init__(self, spec: AgentTurnSpec) -> None:
        object.__setattr__(self, "_utterances", (Utterance(spec.text),) if spec.text.strip() else ())
        object.__setattr__(self, "_person_names", tuple(PersonName(name) for name in spec.person_names))

    @property
    def utterances(self) -> tuple[Utterance, ...]:
        return self._utterances

    @property
    def person_names(self) -> tuple[PersonName, ...]:
        return self._person_names


class HeardSpec(ts.Spec):

    def __init__(self, heard: str, text: str) -> None:
        self.heard = heard
        self.text = text


class Heard(ts.ValueObject):

    _utterances: tuple[Utterance, ...]

    def __init__(self, spec: HeardSpec) -> None:
        if spec.heard not in HEARD:
            raise ValueError(f"what is heard on a call is an utterance or silence, not {spec.heard!r}")
        object.__setattr__(self, "_utterances", (Utterance(spec.text),) if spec.heard == UTTERANCE else ())

    @property
    def utterances(self) -> tuple[Utterance, ...]:
        return self._utterances


class CallProgress(ts.Outcome):
    AGENTS_TURN = enum.auto()
    PERSONS_TURN = enum.auto()
    PERSON_SILENT = enum.auto()
    ENDED = enum.auto()


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

    def __init__(self, call_id: str, person: PersonSpec, turns: tuple[TurnSpec, ...], step: str) -> None:
        self.call_id = call_id
        self.person = person
        self.turns = turns
        self.step = step


class Call(ts.AggregateRoot):

    def __init__(self, spec: CallSpec) -> None:
        self._call_id = CallId(spec.call_id)
        self._person = Person(spec.person)
        self._persona = Persona(_PERSONA)
        self._conversation = Conversation(ConversationSpec(turns=spec.turns))
        self._step = CallStep(spec.step)
        self._listening = False
        self._person_silent = False
        self._person_turn_open = False

    @property
    def identity(self) -> CallId:
        return self._call_id

    @property
    def person(self) -> Person:
        return self._person

    @property
    def persona(self) -> Persona:
        return self._persona

    @property
    def conversation(self) -> Conversation:
        return self._conversation

    @property
    def step(self) -> CallStep:
        return self._step

    @property
    def instructions(self) -> Instructions:
        return Instructions(_INSTRUCTIONS[str(self._step)])

    def agent_said(self, agent_turn: AgentTurn) -> None:
        if agent_turn.utterances:
            self._conversation = self._conversation.with_turn(
                TurnSpec(speaker=AGENT, utterances=tuple(str(u) for u in agent_turn.utterances))
            )
            self._listening = True
            self._person_silent = False
            self._person_turn_open = False
        if agent_turn.person_names and self._step == CallStep(ASK_NAME):
            self._person = Person(
                PersonSpec(name=str(agent_turn.person_names[0]), phone_number=str(self._person.phone_number))
            )
            self._step = CallStep(DONE)

    def heard(self, heard: Heard) -> None:
        if not heard.utterances:
            self._person_silent = True
            return
        for utterance in heard.utterances:
            if self._person_turn_open:
                self._conversation = self._conversation.with_utterance(str(utterance))
            else:
                self._conversation = self._conversation.with_turn(
                    TurnSpec(speaker=PERSON, utterances=(str(utterance),))
                )
                self._person_turn_open = True

    def person_turn_ended(self) -> None:
        self._listening = False
        self._person_silent = False
        self._person_turn_open = False

    def progress(self) -> CallProgress:
        if self._step == CallStep(DONE):
            return CallProgress.ENDED
        if self._person_silent:
            return CallProgress.PERSON_SILENT
        if self._listening:
            return CallProgress.PERSONS_TURN
        return CallProgress.AGENTS_TURN
