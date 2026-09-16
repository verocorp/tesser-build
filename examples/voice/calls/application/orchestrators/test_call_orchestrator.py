from __future__ import annotations

import tesser.testing as ts

import calls.application.orchestrators as orchestrators
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeDialPersonRelay(relays.DialPersonRelay):

    def __init__(self, journal: list[str]) -> None:
        self._journal = journal

    async def run_dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        self._journal.append(f"dial {dial_person_request.call.person.phone_number}")
        return relays.DialPersonResponse(call_id=str(dial_person_request.call.identity))


@ts.fake
class FakeAwaitPersonAnsweredRelay(relays.AwaitPersonAnsweredRelay):

    def __init__(self, journal: list[str]) -> None:
        self._journal = journal

    async def await_person_answered(
        self, await_person_answered_request: relays.AwaitPersonAnsweredRequest
    ) -> relays.AwaitPersonAnsweredResponse:
        self._journal.append("answered")
        return relays.AwaitPersonAnsweredResponse(call_id=await_person_answered_request.call_id)


@ts.fake
class FakeSpeakTurnRelay(relays.SpeakTurnRelay):

    def __init__(self, journal: list[str], name_on_turn: int) -> None:
        self._journal = journal
        self._name_on_turn = name_on_turn
        self.spoken: list[list[str]] = []

    async def run_speak_turn(self, speak_turn_request: relays.SpeakTurnRequest) -> relays.SpeakTurnResponse:
        self.spoken.append([str(turn.utterance) for turn in speak_turn_request.call.conversation.turns])
        self._journal.append(f"speak {len(self.spoken)}")
        if len(self.spoken) == self._name_on_turn:
            return relays.SpeakTurnResponse(
                call_id=str(speak_turn_request.call.identity), text="nice to meet you, Grace", person_names=("Grace",)
            )
        return relays.SpeakTurnResponse(
            call_id=str(speak_turn_request.call.identity), text="hi, may I have your name?", person_names=()
        )


@ts.fake
class FakeAwaitPersonUtteranceRelay(relays.AwaitPersonUtteranceRelay):

    def __init__(self, journal: list[str]) -> None:
        self._journal = journal
        self.awaited = 0

    async def await_person_utterance(
        self, await_person_utterance_request: relays.AwaitPersonUtteranceRequest
    ) -> relays.AwaitPersonUtteranceResponse:
        self.awaited += 1
        self._journal.append(f"hear {self.awaited}")
        return relays.AwaitPersonUtteranceResponse(
            call_id=await_person_utterance_request.call_id, heard=relays.HEARD_UTTERANCE, text="my name is Grace"
        )


@ts.fake
class FakeHangUpRelay(relays.HangUpRelay):

    def __init__(self, journal: list[str]) -> None:
        self._journal = journal

    async def run_hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        self._journal.append("hang up")
        return relays.HangUpResponse(call_id=str(hang_up_request.call.identity))


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

    async def test_a_call_is_dialed_answered_spoken_heard_hung_up_and_recorded_in_that_order(self) -> None:
        journal: list[str] = []
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialPersonRelay(journal),
            FakeAwaitPersonAnsweredRelay(journal),
            FakeSpeakTurnRelay(journal, name_on_turn=2),
            FakeAwaitPersonUtteranceRelay(journal),
            FakeHangUpRelay(journal),
            FakeRecordCallRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert journal == ["dial +15555550100", "answered", "speak 1", "hear 1", "speak 2", "hang up", "record"]

    async def test_the_name_the_agent_recorded_is_the_name_the_call_is_recorded_with(self) -> None:
        journal: list[str] = []
        fake_record_call_relay = FakeRecordCallRelay(journal)
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialPersonRelay(journal),
            FakeAwaitPersonAnsweredRelay(journal),
            FakeSpeakTurnRelay(journal, name_on_turn=2),
            FakeAwaitPersonUtteranceRelay(journal),
            FakeHangUpRelay(journal),
            fake_record_call_relay,
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec(name="Ada"))))

        assert [str(recorded.call.person.name) for recorded in fake_record_call_relay.recorded] == ["Grace"]

    async def test_each_turn_the_agent_speaks_hears_the_whole_conversation_so_far(self) -> None:
        journal: list[str] = []
        fake_speak_turn_relay = FakeSpeakTurnRelay(journal, name_on_turn=2)
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialPersonRelay(journal),
            FakeAwaitPersonAnsweredRelay(journal),
            fake_speak_turn_relay,
            FakeAwaitPersonUtteranceRelay(journal),
            FakeHangUpRelay(journal),
            FakeRecordCallRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert fake_speak_turn_relay.spoken == [[], ["hi, may I have your name?", "my name is Grace"]]

    async def test_the_agent_keeps_asking_until_a_name_is_given(self) -> None:
        journal: list[str] = []
        fake_await_person_utterance_relay = FakeAwaitPersonUtteranceRelay(journal)
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialPersonRelay(journal),
            FakeAwaitPersonAnsweredRelay(journal),
            FakeSpeakTurnRelay(journal, name_on_turn=3),
            fake_await_person_utterance_relay,
            FakeHangUpRelay(journal),
            FakeRecordCallRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert fake_await_person_utterance_relay.awaited == 2

    async def test_conducting_a_call_answers_the_call_id_that_was_recorded(self) -> None:
        journal: list[str] = []
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialPersonRelay(journal),
            FakeAwaitPersonAnsweredRelay(journal),
            FakeSpeakTurnRelay(journal, name_on_turn=1),
            FakeAwaitPersonUtteranceRelay(journal),
            FakeHangUpRelay(journal),
            FakeRecordCallRelay(journal),
        )

        conduct_call_response = await call_orchestrator.conduct_call(
            relays.ConductCallRequest(call=domain.Call(call_spec(call_id="c7")))
        )

        assert conduct_call_response.call_id == "c7"


@ts.fake
class FakeSilentThenSpeakTurnRelay(relays.SpeakTurnRelay):

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


class TestCallOrchestratorWhenTheAgentIsSilent:

    async def test_a_turn_in_which_the_agent_said_nothing_is_spoken_again_rather_than_waited_on(self) -> None:
        journal: list[str] = []
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialPersonRelay(journal),
            FakeAwaitPersonAnsweredRelay(journal),
            FakeSilentThenSpeakTurnRelay(journal),
            FakeAwaitPersonUtteranceRelay(journal),
            FakeHangUpRelay(journal),
            FakeRecordCallRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert journal[:4] == ["dial +15555550100", "answered", "speak 1", "speak 2"]
