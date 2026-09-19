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
SAY_GOODBYE: typing.Final[str] = "say_goodbye"
DONE: typing.Final[str] = "done"
STEPS: typing.Final[tuple[str, ...]] = (ASK_NAME, SAY_GOODBYE, DONE)
SPEECH_STARTED: typing.Final[str] = "speech_started"
TURN_COMPLETED: typing.Final[str] = "turn_completed"
NO_RESPONSE: typing.Final[str] = "no_response"
_PERSONA: typing.Final[str] = (
    "You are a warm, brief receptionist placing a phone call. You speak in short, natural sentences."
)
_INSTRUCTIONS: typing.Final[dict[str, str]] = {
    ASK_NAME: "Greet the person if this is the start of the call and briefly ask for their name. If you already asked, politely ask again.",
    SAY_GOODBYE: "Briefly greet {name} by name and say goodbye.",
    DONE: "The call is over. Say nothing.",
}
_LISTENING_INSTRUCTIONS: typing.Final[str] = (
    "Interpret the latest user turn. Extract a name only if the person gave their own name in that turn. "
    "Do not infer it from assistant messages or invent a name. Do not write a spoken reply. "
    'Return only JSON with this shape: {"person_names": ["name exactly as given"]}. '
    "Use an empty list when no name was given."
)


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


class UserTurnCompletedSpec(ts.Spec):
    def __init__(self, call_id: str, text: str | None) -> None:
        self.call_id = call_id
        self.text = text


class InputDeliveryDecision(ts.Outcome):
    DELIVER = enum.auto()
    IGNORE = enum.auto()


class UserTurnCompleted(ts.ValueObject):
    _call_id: CallId
    _utterances: tuple[Utterance, ...]

    def __init__(self, spec: UserTurnCompletedSpec) -> None:
        object.__setattr__(self, "_call_id", CallId(spec.call_id))
        object.__setattr__(self, "_utterances", ())
        if spec.text is None:
            return
        try:
            utterance = Utterance(spec.text)
        except ValueError:
            return
        object.__setattr__(self, "_utterances", (utterance,))

    @property
    def call_id(self) -> CallId:
        return self._call_id

    @property
    def utterances(self) -> tuple[Utterance, ...]:
        return self._utterances


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
    def __init__(self, text: str) -> None:
        self.text = text


class AgentTurn(ts.ValueObject):
    _utterances: tuple[Utterance, ...]

    def __init__(self, spec: AgentTurnSpec) -> None:
        object.__setattr__(self, "_utterances", (Utterance(spec.text),) if spec.text.strip() else ())

    @property
    def utterances(self) -> tuple[Utterance, ...]:
        return self._utterances


class InterpretedTurnSpec(ts.Spec):
    def __init__(self, person_names: tuple[str, ...]) -> None:
        self.person_names = person_names


class InterpretedTurn(ts.ValueObject):
    _person_names: tuple[PersonName, ...]

    def __init__(self, spec: InterpretedTurnSpec) -> None:
        object.__setattr__(
            self, "_person_names", tuple(PersonName(name.strip()) for name in spec.person_names if name.strip())
        )

    @property
    def person_names(self) -> tuple[PersonName, ...]:
        return self._person_names


class UserSpeechState(enum.Enum):
    SPEAKING = "speaking"
    LISTENING = "listening"
    AWAY = "away"


class UserStateChangedSpec(ts.Spec):
    def __init__(self, call_id: str, new_state: str) -> None:
        self.call_id = call_id
        self.new_state = new_state


class UserStateChanged(ts.ValueObject):
    _call_id: CallId
    _new_state: UserSpeechState

    def __init__(self, spec: UserStateChangedSpec) -> None:
        if spec.new_state not in ("speaking", "listening", "away"):
            raise ValueError("unknown user speech state")
        object.__setattr__(self, "_call_id", CallId(spec.call_id))
        object.__setattr__(self, "_new_state", UserSpeechState(spec.new_state))

    @property
    def call_id(self) -> CallId:
        return self._call_id

    def decide(self) -> InputDeliveryDecision:
        if self._new_state is UserSpeechState.SPEAKING:
            return InputDeliveryDecision.DELIVER
        return InputDeliveryDecision.IGNORE


class PersonInputKind(enum.Enum):
    SPEECH_STARTED = "speech_started"
    TURN_COMPLETED = "turn_completed"
    NO_RESPONSE = "no_response"


class PersonInputSpec(ts.Spec):
    def __init__(self, kind: str, text: str) -> None:
        self.kind = kind
        self.text = text


class PersonInputDecision(ts.Outcome):
    SPEECH_STARTED = enum.auto()
    TURN_COMPLETED = enum.auto()
    NO_RESPONSE = enum.auto()


class PersonInput(ts.ValueObject):
    _kind: PersonInputKind
    _utterances: tuple[Utterance, ...]

    def __init__(self, spec: PersonInputSpec) -> None:
        if spec.kind not in (SPEECH_STARTED, TURN_COMPLETED, NO_RESPONSE):
            raise ValueError("unknown person input")
        object.__setattr__(self, "_kind", PersonInputKind(spec.kind))
        object.__setattr__(
            self, "_utterances", (Utterance(spec.text),) if spec.kind == TURN_COMPLETED and spec.text.strip() else ()
        )

    @property
    def utterances(self) -> tuple[Utterance, ...]:
        return self._utterances

    def decide(self) -> PersonInputDecision:
        match self._kind:
            case PersonInputKind.SPEECH_STARTED:
                return PersonInputDecision.SPEECH_STARTED
            case PersonInputKind.TURN_COMPLETED:
                return PersonInputDecision.TURN_COMPLETED
            case PersonInputKind.NO_RESPONSE:
                return PersonInputDecision.NO_RESPONSE
            case _ as never:
                typing.assert_never(never)


class CallProgress(ts.Outcome):
    AGENTS_TURN = enum.auto()
    AWAITING_RESPONSE = enum.auto()
    PERSON_SPEAKING = enum.auto()
    INTERPRETING_TURN = enum.auto()
    NO_RESPONSE = enum.auto()
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
        self._person_speaking = False
        self._interpreting = False
        self._no_response = False

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
        return Instructions(_INSTRUCTIONS[str(self._step)].format(name=str(self._person.name)))

    @property
    def listening_instructions(self) -> Instructions:
        return Instructions(_LISTENING_INSTRUCTIONS)

    def agent_said(self, agent_turn: AgentTurn) -> None:
        if not agent_turn.utterances:
            return
        self._conversation = self._conversation.with_turn(
            TurnSpec(speaker=AGENT, utterances=tuple(str(u) for u in agent_turn.utterances))
        )
        if self._step == CallStep(SAY_GOODBYE):
            self._step = CallStep(DONE)
            return
        self._listening = True
        self._person_speaking = False
        self._no_response = False

    def receive(self, person_input: PersonInput) -> None:
        match person_input.decide():
            case PersonInputDecision.SPEECH_STARTED:
                self._person_speaking = True
            case PersonInputDecision.TURN_COMPLETED:
                if person_input.utterances:
                    self._conversation = self._conversation.with_turn(
                        TurnSpec(speaker=PERSON, utterances=tuple(str(u) for u in person_input.utterances))
                    )
                self._listening = False
                self._person_speaking = False
                self._interpreting = bool(person_input.utterances)
            case PersonInputDecision.NO_RESPONSE:
                if self._listening and not self._person_speaking:
                    self._no_response = True
            case _ as never:
                typing.assert_never(never)

    def interpreted(self, interpreted_turn: InterpretedTurn) -> None:
        if interpreted_turn.person_names and self._step == CallStep(ASK_NAME):
            self._person = Person(
                PersonSpec(name=str(interpreted_turn.person_names[0]), phone_number=str(self._person.phone_number))
            )
            self._step = CallStep(SAY_GOODBYE)
        self._interpreting = False

    def response_missing(self) -> None:
        self._listening = False
        self._no_response = False

    def progress(self) -> CallProgress:
        if self._step == CallStep(DONE):
            return CallProgress.ENDED
        if self._interpreting:
            return CallProgress.INTERPRETING_TURN
        if self._no_response:
            return CallProgress.NO_RESPONSE
        if self._person_speaking:
            return CallProgress.PERSON_SPEAKING
        if self._listening:
            return CallProgress.AWAITING_RESPONSE
        return CallProgress.AGENTS_TURN
