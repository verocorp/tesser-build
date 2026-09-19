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
        self.ended: list[ports.InterpretTurnRequest] = []

    async def speak_turn(self, speak_turn_request: ports.SpeakTurnRequest) -> ports.SpeakTurnResponse:
        self.spoken.append(speak_turn_request)
        return ports.SpeakTurnResponse(
            call_id=speak_turn_request.call_id,
            text=self._text,
        )


@ts.helper
def call_spec(call_id: str = "c1", name: str = "Ada", phone_number: str = "+15555550100") -> domain.CallSpec:
    return domain.CallSpec(
        call_id=call_id,
        person=domain.PersonSpec(name=name, phone_number=phone_number),
        turns=(
            domain.TurnSpec(speaker="agent", utterances=("hi, may I have your name?",)),
            domain.TurnSpec(speaker="person", utterances=("my name is", "Grace")),
        ),
        step="ask_name",
    )


class TestSpeechActions:
    async def test_a_turns_utterances_reach_the_port_as_one_text(self) -> None:
        fake_speech = FakeSpeech(text="", person_name="")
        speech_actions = application.SpeechActions(fake_speech)

        await speech_actions.speak_turn(relays.SpeakTurnRequest(call=domain.Call(call_spec())))

        assert fake_speech.spoken[0].turns[1].text == "my name is Grace"

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
        assert "ask for their name" in spoken.instructions
