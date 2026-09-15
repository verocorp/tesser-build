from __future__ import annotations

import socket
import threading

import tesser.testing as ts

import calls.adapters.runners as runners
import calls.adapters.runtimes as runtimes
import calls.application.client as client
import calls.application.relays as relays


@ts.fake
class FakeCallsApplicationClient(client.CallsApplicationClient):

    async def record_call(self, record_call_request: relays.RecordCallRequest) -> relays.RecordCallResponse:
        return relays.RecordCallResponse(call_id=record_call_request.call_id)


@ts.fake
class FakeRestateIngress:  # tesser:debt TB072

    def __init__(self, answer: bytes) -> None:
        self._answer = answer
        self._listener = socket.socket()
        self._listener.bind(("127.0.0.1", 0))
        self._listener.listen(1)
        self.port = self._listener.getsockname()[1]
        self.seen: list[bytes] = []
        self._thread = threading.Thread(target=self.serve, daemon=True)  # tesser:debt TB051

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        self._thread.start()

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
        self._thread.join(5)
        self._listener.close()


@ts.helper
def conduct_call_request(
    call_id: str = "c1", person_name: str = "Ada", phone_number: str = "+15555550100"
) -> relays.ConductCallRequest:
    return relays.ConductCallRequest(call_id=call_id, person_name=person_name, phone_number=phone_number)


class TestRestateIngressCallRelays:

    async def test_running_conduct_call_calls_the_workflow_keyed_by_the_call_id(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            relays.ConductCallResponseSnapshot().serialize(relays.ConductCallResponse(call_id="c7"))
        )
        fake_restate_ingress.start()

        conduct_call_response = await runners.RestateIngressCallRelays(
            fake_restate_ingress.base_url, runtimes.RestateCallRuntime(FakeCallsApplicationClient())
        ).run_conduct_call(conduct_call_request(call_id="c7"))
        fake_restate_ingress.close()

        assert conduct_call_response.call_id == "c7"
        assert fake_restate_ingress.seen[0].split(b"\r\n")[0] == b"POST /CallOrchestrator/c7/conduct_call HTTP/1.1"

    async def test_running_person_answered_calls_the_workflows_shared_handler_keyed_by_the_call_id(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            relays.PersonAnsweredResponseSnapshot().serialize(relays.PersonAnsweredResponse(call_id="c7"))
        )
        fake_restate_ingress.start()

        person_answered_response = await runners.RestateIngressCallRelays(
            fake_restate_ingress.base_url, runtimes.RestateCallRuntime(FakeCallsApplicationClient())
        ).run_person_answered(relays.PersonAnsweredRequest(call_id="c7"))
        fake_restate_ingress.close()

        assert person_answered_response.call_id == "c7"
        assert fake_restate_ingress.seen[0].split(b"\r\n")[0] == b"POST /CallOrchestrator/c7/person_answered HTTP/1.1"

    async def test_running_a_person_utterance_calls_the_mailbox_keyed_by_the_call_id(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            relays.PersonUtteranceResponseSnapshot().serialize(relays.PersonUtteranceResponse(call_id="c7"))
        )
        fake_restate_ingress.start()

        person_utterance_response = await runners.RestateIngressCallRelays(
            fake_restate_ingress.base_url, runtimes.RestateCallRuntime(FakeCallsApplicationClient())
        ).run_person_utterance(relays.PersonUtteranceRequest(call_id="c7", text="Ada"))
        fake_restate_ingress.close()

        assert person_utterance_response.call_id == "c7"
        assert fake_restate_ingress.seen[0].split(b"\r\n")[0] == b"POST /CallUtterances/c7/person_utterance HTTP/1.1"
        assert fake_restate_ingress.seen[1] == b'{"call_id": "c7", "text": "Ada"}'
