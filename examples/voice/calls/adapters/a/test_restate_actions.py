from __future__ import annotations

import asyncio
import os
import socket
import typing
import uuid

import tesser.testing as ts
import httpx
import hypercorn.asyncio as hypercorn_asyncio
import hypercorn.config as hypercorn_config
import hypercorn.typing as hypercorn_typing
import restate
import restate.client as restate_client

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


@ts.fake
class FakeSpeechApplicationClient(client.SpeechApplicationClient):
    def __init__(self) -> None:
        self.said: list[relays.SayUtteranceRequest] = []

    async def say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        self.said.append(say_utterance_request)
        return relays.SayUtteranceResponse(call_id=say_utterance_request.call_id)


@ts.helper
def call_spec(call_id: str = "c7", person_name: str = "Grace") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestRestateRecordCall:
    async def test_restate_serves_record_call_and_a_call_made_with_its_handler_reaches_the_application_client(self) -> None:
        call_actions_service = restate.Service(f"CallActions{uuid.uuid4().hex}")
        fake_call_application_client = FakeCallApplicationClient()
        restate_record_call = a.RestateRecordCall(call_actions_service, fake_call_application_client)
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([call_actions_service])),
                hypercorn_config_config,
                shutdown_trigger=shutdown.wait,
            )
        )
        admin = httpx.AsyncClient(base_url=os.environ["RESTATE_ADMIN"], timeout=10.0)
        registered = httpx.Response(503)
        for _ in range(50):
            registered = await admin.post(
                "/deployments",
                json={"uri": f"http://{os.environ['VOICE_CALLBACK_HOST']}:{port}", "force": True},
            )
            if registered.is_success:
                break
            await asyncio.sleep(0.1)

        async with httpx.AsyncClient(base_url=os.environ["RESTATE_URL"], timeout=30.0) as async_client:
            record_call_response = await restate_client.Client(async_client).service_call(
                restate_record_call.handler, relays.RecordCallRequest(call=domain.Call(call_spec()))
            )

        await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
        await admin.aclose()
        shutdown.set()
        await asyncio.wait([serving], timeout=1.0)
        serving.cancel()

        assert registered.is_success
        assert record_call_response == relays.RecordCallResponse(call_id="c7")
        assert [str(request.call.identity) for request in fake_call_application_client.recorded] == ["c7"]


class TestRestateDialPerson:
    async def test_restate_serves_dial_person_and_a_call_made_with_its_handler_reaches_the_application_client(self) -> None:
        dialing_actions_service = restate.Service(f"DialingActions{uuid.uuid4().hex}")
        fake_dialing_application_client = FakeDialingApplicationClient()
        restate_dial_person = a.RestateDialPerson(dialing_actions_service, fake_dialing_application_client)
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([dialing_actions_service])),
                hypercorn_config_config,
                shutdown_trigger=shutdown.wait,
            )
        )
        admin = httpx.AsyncClient(base_url=os.environ["RESTATE_ADMIN"], timeout=10.0)
        registered = httpx.Response(503)
        for _ in range(50):
            registered = await admin.post(
                "/deployments",
                json={"uri": f"http://{os.environ['VOICE_CALLBACK_HOST']}:{port}", "force": True},
            )
            if registered.is_success:
                break
            await asyncio.sleep(0.1)

        async with httpx.AsyncClient(base_url=os.environ["RESTATE_URL"], timeout=30.0) as async_client:
            dial_person_response = await restate_client.Client(async_client).service_call(
                restate_dial_person.handler, relays.DialPersonRequest(call=domain.Call(call_spec()))
            )

        await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
        await admin.aclose()
        shutdown.set()
        await asyncio.wait([serving], timeout=1.0)
        serving.cancel()

        assert registered.is_success
        assert dial_person_response == relays.DialPersonResponse(call_id="c7")
        assert [str(request.call.identity) for request in fake_dialing_application_client.dialed] == ["c7"]


class TestRestateHangUp:
    async def test_restate_serves_hang_up_and_a_call_made_with_its_handler_reaches_the_application_client(self) -> None:
        dialing_actions_service = restate.Service(f"DialingActions{uuid.uuid4().hex}")
        fake_dialing_application_client = FakeDialingApplicationClient()
        restate_hang_up = a.RestateHangUp(dialing_actions_service, fake_dialing_application_client)
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([dialing_actions_service])),
                hypercorn_config_config,
                shutdown_trigger=shutdown.wait,
            )
        )
        admin = httpx.AsyncClient(base_url=os.environ["RESTATE_ADMIN"], timeout=10.0)
        registered = httpx.Response(503)
        for _ in range(50):
            registered = await admin.post(
                "/deployments",
                json={"uri": f"http://{os.environ['VOICE_CALLBACK_HOST']}:{port}", "force": True},
            )
            if registered.is_success:
                break
            await asyncio.sleep(0.1)

        async with httpx.AsyncClient(base_url=os.environ["RESTATE_URL"], timeout=30.0) as async_client:
            hang_up_response = await restate_client.Client(async_client).service_call(
                restate_hang_up.handler, relays.HangUpRequest(call=domain.Call(call_spec()))
            )

        await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
        await admin.aclose()
        shutdown.set()
        await asyncio.wait([serving], timeout=1.0)
        serving.cancel()

        assert registered.is_success
        assert hang_up_response == relays.HangUpResponse(call_id="c7")
        assert [str(request.call.identity) for request in fake_dialing_application_client.hung_up] == ["c7"]


class TestRestateSayUtterance:
    async def test_restate_serves_say_utterance_and_a_call_made_with_its_handler_reaches_the_application_client(self) -> None:
        speech_actions_service = restate.Service(f"SpeechActions{uuid.uuid4().hex}")
        fake_speech_application_client = FakeSpeechApplicationClient()
        restate_say_utterance = a.RestateSayUtterance(speech_actions_service, fake_speech_application_client)
        with socket.socket() as probe:
            probe.bind(("0.0.0.0", 0))
            port = probe.getsockname()[1]
        hypercorn_config_config = hypercorn_config.Config()
        hypercorn_config_config.bind = [f"0.0.0.0:{port}"]
        shutdown = asyncio.Event()
        serving = asyncio.create_task(
            hypercorn_asyncio.serve(
                typing.cast(hypercorn_typing.ASGIFramework, restate.app([speech_actions_service])),
                hypercorn_config_config,
                shutdown_trigger=shutdown.wait,
            )
        )
        admin = httpx.AsyncClient(base_url=os.environ["RESTATE_ADMIN"], timeout=10.0)
        registered = httpx.Response(503)
        for _ in range(50):
            registered = await admin.post(
                "/deployments",
                json={"uri": f"http://{os.environ['VOICE_CALLBACK_HOST']}:{port}", "force": True},
            )
            if registered.is_success:
                break
            await asyncio.sleep(0.1)

        async with httpx.AsyncClient(base_url=os.environ["RESTATE_URL"], timeout=30.0) as async_client:
            say_utterance_response = await restate_client.Client(async_client).service_call(
                restate_say_utterance.handler, relays.SayUtteranceRequest(call_id="c7", text="Hello.")
            )

        await admin.delete(f"/deployments/{registered.json()['id']}", params={"force": "true"})
        await admin.aclose()
        shutdown.set()
        await asyncio.wait([serving], timeout=1.0)
        serving.cancel()

        assert registered.is_success
        assert say_utterance_response == relays.SayUtteranceResponse(call_id="c7")
        assert fake_speech_application_client.said == [relays.SayUtteranceRequest(call_id="c7", text="Hello.")]
