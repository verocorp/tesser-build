from __future__ import annotations

import socket
import threading

import tesser.testing as ts

import calls.adapters.runners as runners
import calls.adapters.runtimes as runtimes
import calls.application.client as client
import calls.application.relays as relays
import calls.domain as domain


@ts.fake
class FakeCallApplicationClient(client.CallApplicationClient):
    async def record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        return relays.RecordCallResponse(call_id=str(record_call_request.call.identity))


@ts.fake
class FakeDialingApplicationClient(client.DialingApplicationClient):
    async def dial_person(self, dial_person_request: relays.DialPersonRequest) -> relays.DialPersonResponse:
        return relays.DialPersonResponse(call_id=str(dial_person_request.call.identity))

    async def hang_up(self, hang_up_request: relays.HangUpRequest) -> relays.HangUpResponse:
        return relays.HangUpResponse(call_id=str(hang_up_request.call.identity))


@ts.fake
class FakeSpeechApplicationClient(client.SpeechApplicationClient):
    async def say_utterance(
        self, say_utterance_request: relays.SayUtteranceRequest
    ) -> relays.SayUtteranceResponse:
        return relays.SayUtteranceResponse(call_id=say_utterance_request.call_id)


@ts.fake
class FakeRestateIngress:  # tesser:debt TB072
    def __init__(self, answer: bytes) -> None:
        self._answer = answer
        self._listener = socket.socket()
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(1)
        self.port = self._listener.getsockname()[1]
        self.seen: list[bytes] = []

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def serve(self) -> None:
        conn, _ = self._listener.accept()
        with conn:
            raw = b""
            while b"\r\n\r\n" not in raw:
                raw += conn.recv(4096)
            head, _, body = raw.partition(b"\r\n\r\n")
            declared = 0
            for line in head.split(b"\r\n"):
                if line.lower().startswith(b"content-length:"):
                    declared = int(line.split(b":", 1)[1])
            while len(body) < declared:
                body += conn.recv(4096)
            self.seen.append(head)
            self.seen.append(body)
            conn.sendall(
                b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: "
                + str(len(self._answer)).encode()
                + b"\r\n\r\n"
                + self._answer
            )

    def close(self) -> None:
        self._listener.close()


@ts.helper
def call_spec(call_id: str = "c1", person_name: str = "") -> domain.CallSpec:
    return domain.CallSpec(call_id=call_id, person_name=person_name)


class TestRestateIngressCallOrchestratorRelay:
    async def test_running_conduct_call_calls_the_workflow_keyed_by_the_call_id(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            relays.ConductCallResponseSnapshot().serialize(relays.ConductCallResponse(call_id="c7"))
        )
        thread = threading.Thread(target=fake_restate_ingress.serve, daemon=True)
        thread.start()

        conduct_call_response = await runners.RestateIngressCallOrchestratorRelay(
            fake_restate_ingress.base_url,
            runtimes.RestateCallRuntime(
                FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
            ),
        ).run_conduct_call(relays.ConductCallRequest(call=domain.Call(call_spec(call_id="c7"))))
        thread.join(5)
        fake_restate_ingress.close()

        assert conduct_call_response.call_id == "c7"
        assert fake_restate_ingress.seen[0].split(b"\r\n")[0] == b"POST /CallOrchestrator/c7/conduct_call HTTP/1.1"

    async def test_running_person_joined_calls_the_workflows_shared_handler_keyed_by_the_call_id(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            relays.PersonJoinedResponseSnapshot().serialize(relays.PersonJoinedResponse(call_id="c7"))
        )
        thread = threading.Thread(target=fake_restate_ingress.serve, daemon=True)
        thread.start()

        person_joined_response = await runners.RestateIngressCallOrchestratorRelay(
            fake_restate_ingress.base_url,
            runtimes.RestateCallRuntime(
                FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
            ),
        ).run_person_joined(relays.PersonJoinedRequest(call_id="c7"))
        thread.join(5)
        fake_restate_ingress.close()

        assert person_joined_response.call_id == "c7"
        assert fake_restate_ingress.seen[0].split(b"\r\n")[0] == b"POST /CallOrchestrator/c7/person_joined HTTP/1.1"

    async def test_running_a_completed_person_turn_hands_the_workflow_what_the_person_said(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            relays.PersonTurnCompletedResponseSnapshot().serialize(relays.PersonTurnCompletedResponse(call_id="c7"))
        )
        thread = threading.Thread(target=fake_restate_ingress.serve, daemon=True)
        thread.start()

        person_turn_completed_response = await runners.RestateIngressCallOrchestratorRelay(
            fake_restate_ingress.base_url,
            runtimes.RestateCallRuntime(
                FakeCallApplicationClient(), FakeDialingApplicationClient(), FakeSpeechApplicationClient()
            ),
        ).run_person_turn_completed(relays.PersonTurnCompletedRequest(call_id="c7", text="Grace"))
        thread.join(5)
        fake_restate_ingress.close()

        assert person_turn_completed_response.call_id == "c7"
        assert (
            fake_restate_ingress.seen[0].split(b"\r\n")[0]
            == b"POST /CallOrchestrator/c7/person_turn_completed HTTP/1.1"
        )
        assert fake_restate_ingress.seen[1] == b'{"call_id": "c7", "text": "Grace"}'
