from __future__ import annotations

import tesser.testing as ts

import calls.application.orchestrators as orchestrators
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeDialingActionsRelay(relays.DialingActionsRelay):
    def __init__(self, journal: list[str]) -> None:
        self._journal = journal

    async def run_dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        self._journal.append("dial_person")
        return relays.DialPersonResponse(call_id=str(dial_person_request.call.identity))

    async def run_hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        self._journal.append("hang_up")
        return relays.HangUpResponse(call_id=str(hang_up_request.call.identity))


@ts.fake
class FakeCallOrchestratorSignalRelay(relays.CallOrchestratorSignalRelay):
    def __init__(self, journal: list[str], text: str) -> None:
        self._journal = journal
        self._text = text

    async def await_person_joined(
        self, await_person_joined_request: relays.AwaitPersonJoinedRequest
    ) -> relays.AwaitPersonJoinedResponse:
        self._journal.append("await_person_joined")
        return relays.AwaitPersonJoinedResponse(call_id=await_person_joined_request.call_id)

    async def await_person_turn_completed(
        self, await_person_turn_completed_request: relays.AwaitPersonTurnCompletedRequest
    ) -> relays.AwaitPersonTurnCompletedResponse:
        self._journal.append("await_person_turn_completed")
        return relays.AwaitPersonTurnCompletedResponse(call_id=await_person_turn_completed_request.call_id, text=self._text)


@ts.fake
class FakeSpeechActionsRelay(relays.SpeechActionsRelay):
    def __init__(self, journal: list[str]) -> None:
        self._journal = journal

    async def run_say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        self._journal.append(f"say_utterance {say_utterance_request.text}")
        return relays.SayUtteranceResponse(call_id=say_utterance_request.call_id)


@ts.fake
class FakeCallActionsRelay(relays.CallActionsRelay):
    def __init__(self, journal: list[str]) -> None:
        self._journal = journal
        self.recorded: list[relays.RecordCallRequest] = []

    async def run_record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        self._journal.append("record_call")
        self.recorded.append(record_call_request)
        return relays.RecordCallResponse(call_id=str(record_call_request.call.identity))


@ts.helper
def call_spec(call_id: str = "c1", person_name: str = "") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestCallOrchestrator:
    async def test_a_call_dials_asks_for_the_name_greets_the_person_and_hangs_up(self) -> None:
        journal: list[str] = []
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingActionsRelay(journal),
            FakeCallOrchestratorSignalRelay(journal, "Grace"),
            FakeSpeechActionsRelay(journal),
            FakeCallActionsRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert journal == [
            "dial_person",
            "await_person_joined",
            "say_utterance Hello. Please tell me your first name.",
            "await_person_turn_completed",
            "say_utterance Nice to meet you, Grace. Goodbye.",
            "hang_up",
            "record_call",
        ]

    async def test_the_recorded_call_carries_the_name_the_person_said(self) -> None:
        journal: list[str] = []
        fake_call_actions_relay = FakeCallActionsRelay(journal)
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingActionsRelay(journal),
            FakeCallOrchestratorSignalRelay(journal, "Grace"),
            FakeSpeechActionsRelay(journal),
            fake_call_actions_relay,
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert [str(recorded.call.person_name) for recorded in fake_call_actions_relay.recorded] == ["Grace"]

    async def test_a_name_said_with_punctuation_is_recorded_without_it(self) -> None:
        journal: list[str] = []
        fake_call_actions_relay = FakeCallActionsRelay(journal)
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingActionsRelay(journal),
            FakeCallOrchestratorSignalRelay(journal, "Sarah."),
            FakeSpeechActionsRelay(journal),
            fake_call_actions_relay,
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert [str(recorded.call.person_name) for recorded in fake_call_actions_relay.recorded] == ["Sarah"]

    async def test_conducting_a_call_answers_the_call_id_it_recorded(self) -> None:
        journal: list[str] = []
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingActionsRelay(journal),
            FakeCallOrchestratorSignalRelay(journal, "Grace"),
            FakeSpeechActionsRelay(journal),
            FakeCallActionsRelay(journal),
        )

        conduct_call_response = await call_orchestrator.conduct_call(
            relays.ConductCallRequest(call=domain.Call(call_spec(call_id="c7")))
        )

        assert conduct_call_response.call_id == "c7"
