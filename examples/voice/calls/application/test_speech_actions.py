from __future__ import annotations

import tesser.testing as ts

import calls.application as application
import calls.application.ports as ports
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeSpeech(ports.Speech):

    def __init__(self, text: str, person_name: str) -> None:
        self._text = text
        self._person_name = person_name
        self.spoken: list[ports.SpeakTurnRequest] = []
        self.ended: list[ports.EndPersonTurnRequest] = []

    async def speak_turn(self, speak_turn_request: ports.SpeakTurnRequest) -> ports.SpeakTurnResponse:
        self.spoken.append(speak_turn_request)
        return ports.SpeakTurnResponse(
            call_id=speak_turn_request.call_id,
            text=self._text,
            person_names=(self._person_name,) if self._person_name else (),
        )

    async def end_person_turn(
        self, end_person_turn_request: ports.EndPersonTurnRequest
    ) -> ports.EndPersonTurnResponse:
        self.ended.append(end_person_turn_request)
        return ports.EndPersonTurnResponse(call_id=end_person_turn_request.call_id)


@ts.helper
def call_spec(call_id: str = "c1", name: str = "Ada", phone_number: str = "+15555550100") -> domain.CallSpec:
    return domain.CallSpec(
        call_id=call_id,
        person=domain.PersonSpec(name=name, phone_number=phone_number),
        turns=(
            domain.TurnSpec(speaker="agent", text="hi, may I have your name?"),
            domain.TurnSpec(speaker="person", text="my name is Grace"),
        ),
        step="ask_name",
    )


class TestSpeechActions:

    async def test_speaking_a_turn_hands_the_port_the_calls_persona_turns_and_instructions(self) -> None:
        fake_speech = FakeSpeech(text="nice to meet you, Grace", person_name="Grace")
        speech_actions = application.SpeechActions(fake_speech)

        await speech_actions.speak_turn(relays.SpeakTurnRequest(call=domain.Call(call_spec(call_id="c7"))))

        spoken = fake_speech.spoken[0]
        assert spoken.call_id == "c7"
        assert "receptionist" in spoken.persona
        assert [(turn.spoken_by, turn.text) for turn in spoken.turns] == [
            (ports.SpokenBy.AGENT, "hi, may I have your name?"),
            (ports.SpokenBy.PERSON, "my name is Grace"),
        ]
        assert "person_gave_name" in spoken.instructions

    async def test_speaking_a_turn_answers_what_the_agent_said_and_the_name_it_recorded(self) -> None:
        speech_actions = application.SpeechActions(FakeSpeech(text="nice to meet you, Grace", person_name="Grace"))

        speak_turn_response = await speech_actions.speak_turn(
            relays.SpeakTurnRequest(call=domain.Call(call_spec(call_id="c7")))
        )

        assert (speak_turn_response.call_id, speak_turn_response.text, speak_turn_response.person_names) == (
            "c7",
            "nice to meet you, Grace",
            ("Grace",),
        )

    async def test_a_turn_with_no_name_given_answers_no_person_name(self) -> None:
        speech_actions = application.SpeechActions(FakeSpeech(text="sorry, what was that?", person_name=""))

        speak_turn_response = await speech_actions.speak_turn(relays.SpeakTurnRequest(call=domain.Call(call_spec())))

        assert speak_turn_response.person_names == ()

    async def test_ending_the_persons_turn_hands_the_port_the_call_it_is_on(self) -> None:
        fake_speech = FakeSpeech(text="", person_name="")
        speech_actions = application.SpeechActions(fake_speech)

        await speech_actions.end_person_turn(
            relays.EndPersonTurnRequest(call=domain.Call(call_spec(call_id="c7")))
        )

        assert [ended.call_id for ended in fake_speech.ended] == ["c7"]

    async def test_ending_the_persons_turn_answers_the_call_id(self) -> None:
        speech_actions = application.SpeechActions(FakeSpeech(text="", person_name=""))

        end_person_turn_response = await speech_actions.end_person_turn(
            relays.EndPersonTurnRequest(call=domain.Call(call_spec(call_id="c7")))
        )

        assert end_person_turn_response.call_id == "c7"
