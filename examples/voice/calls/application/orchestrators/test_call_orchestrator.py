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
    def __init__(self, journal: list[str]) -> None:
        self._journal = journal
        self.spoken: list[relays.SpeakTurnRequest] = []

    async def run_speak_turn(self, speak_turn_request: relays.SpeakTurnRequest) -> relays.SpeakTurnResponse:
        self.spoken.append(speak_turn_request)
        self._journal.append("speak")
        return relays.SpeakTurnResponse(call_id=str(speak_turn_request.call.identity), text="Hello")


@ts.fake
class FakeInterpretationRelay(relays.InterpretationRelay):
    def __init__(self, journal: list[str]) -> None:
        self._journal = journal
        self.interpreted: list[relays.InterpretTurnRequest] = []

    async def run_interpret_turn(
        self, interpret_turn_request: relays.InterpretTurnRequest
    ) -> relays.InterpretTurnResponse:
        self.interpreted.append(interpret_turn_request)
        self._journal.append("interpret")
        return relays.InterpretTurnResponse(call_id=str(interpret_turn_request.call.identity), person_names=("Grace",))


@ts.fake
class FakePersonRelay(relays.PersonRelay):
    def __init__(self, journal: list[str], kinds: list[str]) -> None:
        self._journal = journal
        self._kinds = kinds
        self.within_seconds: list[int | None] = []

    async def await_person_answered(
        self, await_person_answered_request: relays.AwaitPersonAnsweredRequest
    ) -> relays.AwaitPersonAnsweredResponse:
        self._journal.append("answered")
        return relays.AwaitPersonAnsweredResponse(call_id=await_person_answered_request.call_id)

    async def await_person_input(
        self, await_person_input_request: relays.AwaitPersonInputRequest
    ) -> relays.AwaitPersonInputResponse:
        self.within_seconds.append(await_person_input_request.within_seconds)
        kind = self._kinds.pop(0)
        self._journal.append(kind)
        return relays.AwaitPersonInputResponse(
            call_id=await_person_input_request.call_id,
            kind=kind,
            text="my name is Grace" if kind == relays.INPUT_TURN_COMPLETED else "",
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
    async def test_completed_turn_is_interpreted_and_answered_without_waiting_for_silence(self) -> None:
        journal: list[str] = []
        fake_person_relay = FakePersonRelay(journal, [relays.INPUT_SPEECH_STARTED, relays.INPUT_TURN_COMPLETED])
        fake_record_call_relay = FakeRecordCallRelay(journal)
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            FakeSpeechRelay(journal),
            fake_person_relay,
            fake_record_call_relay,
            FakeInterpretationRelay(journal),
        )

        conduct_call_response = await call_orchestrator.conduct_call(
            relays.ConductCallRequest(call=domain.Call(call_spec()))
        )

        assert journal == [
            "dial +15555550100",
            "answered",
            "speak",
            "speech_started",
            "turn_completed",
            "interpret",
            "speak",
            "hang up",
            "record",
        ]
        assert fake_person_relay.within_seconds == [8, None]
        assert str(fake_record_call_relay.recorded[0].call.person.name) == "Grace"
        assert conduct_call_response.call_id == "c1"

    async def test_no_response_prompts_again_without_interpreting_nonexistent_input(self) -> None:
        journal: list[str] = []
        fake_person_relay = FakePersonRelay(journal, [relays.INPUT_NO_RESPONSE, relays.INPUT_TURN_COMPLETED])
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            FakeSpeechRelay(journal),
            fake_person_relay,
            FakeRecordCallRelay(journal),
            FakeInterpretationRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert journal == [
            "dial +15555550100",
            "answered",
            "speak",
            "no_response",
            "speak",
            "turn_completed",
            "interpret",
            "speak",
            "hang up",
            "record",
        ]
        assert fake_person_relay.within_seconds == [8, 8]

    async def test_repeated_speech_starts_do_not_rearm_the_no_response_deadline(self) -> None:
        journal: list[str] = []
        fake_person_relay = FakePersonRelay(
            journal, [relays.INPUT_SPEECH_STARTED, relays.INPUT_SPEECH_STARTED, relays.INPUT_TURN_COMPLETED]
        )
        call_orchestrator = orchestrators.CallOrchestrator(
            FakeDialingRelay(journal),
            FakeSpeechRelay(journal),
            fake_person_relay,
            FakeRecordCallRelay(journal),
            FakeInterpretationRelay(journal),
        )

        await call_orchestrator.conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec())))

        assert fake_person_relay.within_seconds == [8, None, None]
