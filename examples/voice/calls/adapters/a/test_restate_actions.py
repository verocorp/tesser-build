from __future__ import annotations

import typing

import tesser.testing as ts
import restate

import calls.adapters.a as a
import calls.application.client as client
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeCallApplicationClient(client.CallApplicationClient):
    def __init__(self) -> None:
        self.recorded: list[relays.RecordCallRequest] = []

    async def record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        self.recorded.append(record_call_request)
        return relays.RecordCallResponse(call_id=str(record_call_request.call.identity))


class TestRestateRecordCall:
    def test_it_registers_its_handler_under_the_operation_on_the_service_it_is_handed(self) -> None:
        call_actions_service = restate.Service("CallActions")

        a.RestateRecordCall(call_actions_service, FakeCallApplicationClient())

        assert sorted(call_actions_service.handlers) == ["record_call"]

    async def test_the_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_call_application_client = FakeCallApplicationClient()
        record_call_request = relays.RecordCallRequest(
            call=domain.Call(domain.CallSpec(call_id="c7", person_name="Grace"))
        )

        await a.RestateRecordCall(restate.Service("CallActions"), fake_call_application_client).handler(
            typing.cast(restate.Context, None), record_call_request
        )

        assert fake_call_application_client.recorded == [record_call_request]


@ts.fake
class FakeDialingApplicationClient(client.DialingApplicationClient):
    def __init__(self) -> None:
        self.dialed: list[relays.DialPersonRequest] = []
        self.hung_up: list[relays.HangUpRequest] = []

    async def dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        self.dialed.append(dial_person_request)
        return relays.DialPersonResponse(call_id=str(dial_person_request.call.identity))

    async def hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        self.hung_up.append(hang_up_request)
        return relays.HangUpResponse(call_id=str(hang_up_request.call.identity))


class TestRestateDialPerson:
    def test_it_registers_its_handler_under_the_operation_on_the_service_it_is_handed(self) -> None:
        dialing_actions_service = restate.Service("DialingActions")

        a.RestateDialPerson(dialing_actions_service, FakeDialingApplicationClient())

        assert sorted(dialing_actions_service.handlers) == ["dial_person"]

    async def test_the_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_dialing_application_client = FakeDialingApplicationClient()
        dial_person_request = relays.DialPersonRequest(
            call=domain.Call(domain.CallSpec(call_id="c7", person_name=""))
        )

        await a.RestateDialPerson(restate.Service("DialingActions"), fake_dialing_application_client).handler(
            typing.cast(restate.Context, None), dial_person_request
        )

        assert fake_dialing_application_client.dialed == [dial_person_request]


class TestRestateHangUp:
    def test_it_registers_its_handler_under_the_operation_on_the_service_it_is_handed(self) -> None:
        dialing_actions_service = restate.Service("DialingActions")

        a.RestateHangUp(dialing_actions_service, FakeDialingApplicationClient())

        assert sorted(dialing_actions_service.handlers) == ["hang_up"]

    async def test_the_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_dialing_application_client = FakeDialingApplicationClient()
        hang_up_request = relays.HangUpRequest(
            call=domain.Call(domain.CallSpec(call_id="c7", person_name=""))
        )

        await a.RestateHangUp(restate.Service("DialingActions"), fake_dialing_application_client).handler(
            typing.cast(restate.Context, None), hang_up_request
        )

        assert fake_dialing_application_client.hung_up == [hang_up_request]


@ts.fake
class FakeSpeechApplicationClient(client.SpeechApplicationClient):
    def __init__(self) -> None:
        self.said: list[relays.SayUtteranceRequest] = []

    async def say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        self.said.append(say_utterance_request)
        return relays.SayUtteranceResponse(call_id=say_utterance_request.call_id)


class TestRestateSayUtterance:
    def test_it_registers_its_handler_under_the_operation_on_the_service_it_is_handed(self) -> None:
        speech_actions_service = restate.Service("SpeechActions")

        a.RestateSayUtterance(speech_actions_service, FakeSpeechApplicationClient())

        assert sorted(speech_actions_service.handlers) == ["say_utterance"]

    async def test_the_handler_hands_the_request_to_the_application_client(self) -> None:
        fake_speech_application_client = FakeSpeechApplicationClient()
        say_utterance_request = relays.SayUtteranceRequest(call_id="c7", text="Hello.")

        await a.RestateSayUtterance(restate.Service("SpeechActions"), fake_speech_application_client).handler(
            typing.cast(restate.Context, None), say_utterance_request
        )

        assert fake_speech_application_client.said == [say_utterance_request]
