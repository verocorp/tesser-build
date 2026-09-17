from __future__ import annotations

import tesser.testing as ts

import calls.application.orchestrators as orchestrators
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeDialingRelay(relays.DialingRelay):

    def __init__(self, journal: list[str]) -> None:
        self._journal = journal

    async def run_dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        self._journal.append(f"dial {dial_person_request.call.person.phone_number}")
        return relays.DialPersonResponse(call_id=str(dial_person_request.call.identity))

    async def run_hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        self._journal.append("hang up")
        return relays.HangUpResponse(call_id=str(hang_up_request.call.identity))


@ts.fake
class FakeSpeechRelay(relays.SpeechRelay):

    def __init__(self, journal: list[str], name_on_turn: int) -> None:
        self._journal = journal
        self._name_on_turn = name_on_turn
        self.spoken: list[list[list[str]]] = []
        self.ended = 0

    async def run_speak_turn(self, speak_turn_request: relays.SpeakTurnRequest) -> relays.SpeakTurnResponse:
        self.spoken.append(
            [[str(u) for u in turn.utterances] for turn in speak_turn_request.call.conversation.turns]
        )
        self._journal.append(f"speak {len(self.spoken)}")
        if len(self.spoken) == self._name_on_turn:
            return relays.SpeakTurnResponse(
                call_id=str(speak_turn_request.call.identity), text="nice to meet you, Grace", person_names=("Grace",)
            )
        return relays.SpeakTurnResponse(
            call_id=str(speak_turn_request.call.identity), text="hi, may I have your name?", person_names=()
        )

    async def run_end_person_turn(
        self, end_person_turn_request: relays.EndPersonTurnRequest
    ) -> relays.EndPersonTurnResponse:
        self.ended += 1
        self._journal.append("end person turn")
        return relays.EndPersonTurnResponse(call_id=str(end_person_turn_request.call.identity))


@ts.fake
class FakePersonRelay(relays.PersonRelay):

    def __init__(self, journal: list[str], said: list[str]) -> None:
        self._journal = journal
        self._said = said
        self.awaited = 0
        self.within_seconds: list[int] = []

    async def await_person_answered(
        self, await_person_answered_request: relays.AwaitPersonAnsweredRequest
    ) -> relays.AwaitPersonAnsweredResponse:
        self._journal.append("answered")
        return relays.AwaitPersonAnsweredResponse(call_id=await_person_answered_request.call_id)

    async def await_person_utterance(
        self, await_person_utterance_request: relays.AwaitPersonUtteranceRequest
    ) -> relays.AwaitPersonUtteranceResponse:
        self.within_seconds.append(await_person_utterance_request.within_seconds)
        text = self._said[self.awaited % len(self._said)]
        self.awaited += 1
        self._journal.append(f"hear {self.awaited}" if text else f"silence {self.awaited}")
        return relays.AwaitPersonUtteranceResponse(
            call_id=await_person_utterance_request.call_id,
            heard=relays.HEARD_UTTERANCE if text else relays.HEARD_SILENCE,
            text=text,
        )


@ts.fake
class FakeRecordCallRelay(relays.RecordCallRelay):

    def __init__(self, journal: list[str]) -> None:
        self._journal = journal
        self.recorded: list[relays.RecordCallRequest] = []

    async def run_record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        self._journal.append("record")
        self.recorded.append(record_call_request)
        return relays.RecordCallResponse(call_id=str(record_call_request.call.identity))


@ts.helper
def call_spec(call_id: str = "c1", name: str = "Ada", phone_number: str = "+15555550100") -> domain.CallSpec:
    return domain.CallSpec(
        call_id=call_id, person=domain.PersonSpec(name=name, phone_number=phone_number), turns=(), step="ask_name"
    )


class TestCallOrchestrator:

    async def test_a_call_is_dialed_answered_spoken_heard_ended_hung_up_and_recorded_in_that_order(self) -> None:
        journal: list[str] = []
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            FakeSpeechRelay(journal, name_on_turn=2),
            FakePersonRelay(journal, said=["my name is Grace", ""]),
            FakeRecordCallRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert journal == [
            "dial +15555550100",
            "answered",
            "speak 1",
            "hear 1",
            "silence 2",
            "end person turn",
            "speak 2",
            "hang up",
            "record",
        ]

    async def test_the_name_the_agent_recorded_is_the_name_the_call_is_recorded_with(self) -> None:
        journal: list[str] = []
        fake_record_call_relay = FakeRecordCallRelay(journal)
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            FakeSpeechRelay(journal, name_on_turn=2),
            FakePersonRelay(journal, said=["my name is Grace", ""]),
            fake_record_call_relay,
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec(name="Ada"))))

        assert [str(recorded.call.person.name) for recorded in fake_record_call_relay.recorded] == ["Grace"]

    async def test_each_turn_the_agent_speaks_hears_the_whole_conversation_so_far(self) -> None:
        journal: list[str] = []
        fake_speech_relay = FakeSpeechRelay(journal, name_on_turn=2)
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            fake_speech_relay,
            FakePersonRelay(journal, said=["my name is Grace", ""]),
            FakeRecordCallRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert fake_speech_relay.spoken == [[], [["hi, may I have your name?"], ["my name is Grace"]]]

    async def test_everything_the_person_says_before_falling_silent_reaches_the_agent_as_one_turn(self) -> None:
        journal: list[str] = []
        fake_speech_relay = FakeSpeechRelay(journal, name_on_turn=2)
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            fake_speech_relay,
            FakePersonRelay(journal, said=["my name is", "Grace", ""]),
            FakeRecordCallRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert fake_speech_relay.spoken[1] == [["hi, may I have your name?"], ["my name is", "Grace"]]

    async def test_the_persons_turn_is_ended_once_for_each_silence(self) -> None:
        journal: list[str] = []
        fake_speech_relay = FakeSpeechRelay(journal, name_on_turn=3)
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            fake_speech_relay,
            FakePersonRelay(journal, said=["my name is Grace", ""]),
            FakeRecordCallRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert fake_speech_relay.ended == 2

    async def test_the_agent_keeps_asking_until_a_name_is_given(self) -> None:
        journal: list[str] = []
        fake_person_relay = FakePersonRelay(journal, said=["my name is Grace", ""])
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            FakeSpeechRelay(journal, name_on_turn=3),
            fake_person_relay,
            FakeRecordCallRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert fake_person_relay.awaited == 4

    async def test_the_person_is_waited_on_within_the_silence_the_orchestrator_allows(self) -> None:
        journal: list[str] = []
        fake_person_relay = FakePersonRelay(journal, said=["my name is Grace", ""])
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            FakeSpeechRelay(journal, name_on_turn=2),
            fake_person_relay,
            FakeRecordCallRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert fake_person_relay.within_seconds == [8, 8]

    async def test_conducting_a_call_answers_the_call_id_that_was_recorded(self) -> None:
        journal: list[str] = []
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            FakeSpeechRelay(journal, name_on_turn=1),
            FakePersonRelay(journal, said=["my name is Grace", ""]),
            FakeRecordCallRelay(journal),
        )

        conduct_call_response = await call_orchestrator.conduct_call(
            relays.ConductCallRequest(call=domain.Call(call_spec(call_id="c7")))
        )

        assert conduct_call_response.call_id == "c7"


@ts.fake
class FakeSilentThenSpeechRelay(relays.SpeechRelay):

    def __init__(self, journal: list[str]) -> None:
        self._journal = journal
        self.spoken = 0

    async def run_speak_turn(self, speak_turn_request: relays.SpeakTurnRequest) -> relays.SpeakTurnResponse:
        self.spoken += 1
        self._journal.append(f"speak {self.spoken}")
        if self.spoken == 1:
            return relays.SpeakTurnResponse(call_id=str(speak_turn_request.call.identity), text="", person_names=())
        return relays.SpeakTurnResponse(
            call_id=str(speak_turn_request.call.identity), text="nice to meet you, Grace", person_names=("Grace",)
        )

    async def run_end_person_turn(
        self, end_person_turn_request: relays.EndPersonTurnRequest
    ) -> relays.EndPersonTurnResponse:
        self._journal.append("end person turn")
        return relays.EndPersonTurnResponse(call_id=str(end_person_turn_request.call.identity))


class TestCallOrchestratorWhenTheAgentIsSilent:

    async def test_a_turn_in_which_the_agent_said_nothing_is_spoken_again_rather_than_waited_on(self) -> None:
        journal: list[str] = []
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            FakeSilentThenSpeechRelay(journal),
            FakePersonRelay(journal, said=["my name is Grace", ""]),
            FakeRecordCallRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert journal[:4] == ["dial +15555550100", "answered", "speak 1", "speak 2"]
