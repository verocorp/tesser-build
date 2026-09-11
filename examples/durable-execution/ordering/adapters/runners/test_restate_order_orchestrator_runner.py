from __future__ import annotations

import asyncio
import socket
import threading

import tesser.testing as ts
import pytest

import ordering.adapters.runners as runners
import ordering.adapters.runtimes as runtimes
import ordering.application.client as client
import ordering.application.ports as ports
import ordering.application.relays as relays
import ordering.domain as domain


@ts.fake
class FakeOrderingApplicationClient(client.OrderingApplicationClient):

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        return relays.PriceProductResponse(cents=250)


@ts.fake
class FakePurchaseApplicationClient(client.PurchaseApplicationClient):

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        return relays.TakePaymentResponse(
            order_id=take_payment_request.order_id,
            reference=f"pay-{take_payment_request.order_id}",
            cents=take_payment_request.cents,
        )


@ts.helper
def order_orchestrator_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> relays.OrderOrchestratorRequest:
    return relays.OrderOrchestratorRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestRestateOrderOrchestratorRunner:

    def test_starting_sends_the_workflow_keyed_by_the_orders_id(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        seen: list[bytes] = []

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
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
                seen.append(head)
                seen.append(body)
                answer = b'{"invocationId": "inv_1", "status": "Accepted"}'
                conn.sendall(
                    b"HTTP/1.1 202 Accepted\r\ncontent-type: application/json\r\ncontent-length: "
                    + str(len(answer)).encode()
                    + b"\r\n\r\n"
                    + answer
                )

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            start_order_orchestrator_response = asyncio.run(
                runners.RestateOrderOrchestratorRunner(
                    f"http://127.0.0.1:{port}",
                    runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                ).start_order_orchestrator(order_orchestrator_request())
            )
        finally:
            thread.join(5)
            listener.close()

        assert start_order_orchestrator_response.order_id == "o1"
        assert seen[0].split(b"\r\n")[0] == b"POST /OrderOrchestrator/o1/run/send HTTP/1.1"
        assert seen[1] == relays.OrderOrchestratorRequestSnapshot().serialize(
            order_orchestrator_request()
        )

    def test_the_key_is_encoded_so_an_order_id_cannot_reshape_the_path(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        seen: list[bytes] = []

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
            with conn:
                raw = b""
                while b"\r\n\r\n" not in raw:
                    raw += conn.recv(4096)
                seen.append(raw.partition(b"\r\n\r\n")[0])
                answer = b'{"invocationId": "inv_1", "status": "Accepted"}'
                conn.sendall(
                    b"HTTP/1.1 202 Accepted\r\ncontent-type: application/json\r\ncontent-length: "
                    + str(len(answer)).encode()
                    + b"\r\n\r\n"
                    + answer
                )

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            start_order_orchestrator_response = asyncio.run(
                runners.RestateOrderOrchestratorRunner(
                    f"http://127.0.0.1:{port}",
                    runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                ).start_order_orchestrator(order_orchestrator_request(order_id="../admin?x=1#f"))
            )
        finally:
            thread.join(5)
            listener.close()

        assert start_order_orchestrator_response.order_id == "../admin?x=1#f"
        assert seen[0].split(b"\r\n")[0] == (
            b"POST /OrderOrchestrator/..%2Fadmin%3Fx%3D1%23f/run/send HTTP/1.1"
        )

    def test_an_order_already_started_is_the_engines_conflict(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
            with conn:
                while b"\r\n\r\n" not in conn.recv(4096):
                    continue
                conn.sendall(b"HTTP/1.1 409 Conflict\r\ncontent-length: 0\r\n\r\n")

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(ports.EngineConflict) as excinfo:
                asyncio.run(
                    runners.RestateOrderOrchestratorRunner(
                        f"http://127.0.0.1:{port}",
                        runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                    ).start_order_orchestrator(order_orchestrator_request())
                )
        finally:
            thread.join(5)
            listener.close()

        assert excinfo.value.message == "Conflict"

    def test_a_refused_send_is_an_infra_error(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
            with conn:
                while b"\r\n\r\n" not in conn.recv(4096):
                    continue
                conn.sendall(b"HTTP/1.1 404 Not Found\r\ncontent-length: 0\r\n\r\n")

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(ports.EngineUnavailable):
                asyncio.run(
                    runners.RestateOrderOrchestratorRunner(
                        f"http://127.0.0.1:{port}",
                        runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                    ).start_order_orchestrator(order_orchestrator_request())
                )
        finally:
            thread.join(5)
            listener.close()

    def test_an_unreachable_ingress_is_an_infra_error(self) -> None:
        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            port = closed.getsockname()[1]

        with pytest.raises(ports.EngineUnavailable):
            asyncio.run(
                runners.RestateOrderOrchestratorRunner(
                    f"http://127.0.0.1:{port}",
                    runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                ).start_order_orchestrator(order_orchestrator_request())
            )

    def test_running_calls_the_workflow_and_answers_with_its_result(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        seen: list[bytes] = []

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
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
                seen.append(head)
                seen.append(body)
                answer = relays.OrderOrchestratorResponseSnapshot().serialize(
                    relays.OrderOrchestratorResponse(order_id="o1", total_cents=500)
                )
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: "
                    + str(len(answer)).encode()
                    + b"\r\n\r\n"
                    + answer
                )

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            order_orchestrator_response = asyncio.run(
                runners.RestateOrderOrchestratorRunner(
                    f"http://127.0.0.1:{port}",
                    runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                ).run_order_orchestrator(order_orchestrator_request())
            )
        finally:
            thread.join(5)
            listener.close()

        assert order_orchestrator_response == relays.OrderOrchestratorResponse(
            order_id="o1", total_cents=500
        )
        assert seen[0].split(b"\r\n")[0] == b"POST /OrderOrchestrator/o1/run HTTP/1.1"
        assert seen[1] == relays.OrderOrchestratorRequestSnapshot().serialize(
            order_orchestrator_request()
        )

    def test_an_order_already_placed_is_the_engines_conflict(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
            with conn:
                while b"\r\n\r\n" not in conn.recv(4096):
                    continue
                answer = b'{"code":409,"message":"the workflow method was already invoked"}'
                conn.sendall(
                    b"HTTP/1.1 409 Conflict\r\ncontent-type: application/json\r\ncontent-length: "
                    + str(len(answer)).encode()
                    + b"\r\n\r\n"
                    + answer
                )

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(ports.EngineConflict) as excinfo:
                asyncio.run(
                    runners.RestateOrderOrchestratorRunner(
                        f"http://127.0.0.1:{port}",
                        runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                    ).run_order_orchestrator(order_orchestrator_request())
                )
        finally:
            thread.join(5)
            listener.close()

        assert excinfo.value.message == "the workflow method was already invoked"

    def test_a_workflow_that_ended_terminally_answers_with_the_engines_missing(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
            with conn:
                while b"\r\n\r\n" not in conn.recv(4096):
                    continue
                answer = b'{"code":404,"message":"no price for sku \'nope\'"}'
                conn.sendall(
                    b"HTTP/1.1 404 Not Found\r\ncontent-type: application/json\r\ncontent-length: "
                    + str(len(answer)).encode()
                    + b"\r\n\r\n"
                    + answer
                )

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(ports.EngineMissing) as excinfo:
                asyncio.run(
                    runners.RestateOrderOrchestratorRunner(
                        f"http://127.0.0.1:{port}",
                        runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                    ).run_order_orchestrator(order_orchestrator_request(sku="nope"))
                )
        finally:
            thread.join(5)
            listener.close()

        assert excinfo.value.message == "no price for sku 'nope'"

    def test_a_workflow_that_refused_its_input_answers_as_the_engines_rejection(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
            with conn:
                while b"\r\n\r\n" not in conn.recv(4096):
                    continue
                answer = b'{"code":422,"message":"an order is for at least one unit"}'
                conn.sendall(
                    b"HTTP/1.1 422 Unprocessable Entity\r\ncontent-type: application/json\r\ncontent-length: "
                    + str(len(answer)).encode()
                    + b"\r\n\r\n"
                    + answer
                )

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(ports.EngineRejected) as excinfo:
                asyncio.run(
                    runners.RestateOrderOrchestratorRunner(
                        f"http://127.0.0.1:{port}",
                        runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                    ).run_order_orchestrator(order_orchestrator_request())
                )
        finally:
            thread.join(5)
            listener.close()

        assert excinfo.value.message == "an order is for at least one unit"

    def test_a_status_the_domain_does_not_own_is_an_infra_error_even_with_a_code(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
            with conn:
                while b"\r\n\r\n" not in conn.recv(4096):
                    continue
                answer = b'{"code":500,"message":"Unable to parse an input argument"}'
                conn.sendall(
                    b"HTTP/1.1 500 Internal Server Error\r\ncontent-type: application/json\r\ncontent-length: "
                    + str(len(answer)).encode()
                    + b"\r\n\r\n"
                    + answer
                )

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(ports.EngineUnavailable) as excinfo:
                asyncio.run(
                    runners.RestateOrderOrchestratorRunner(
                        f"http://127.0.0.1:{port}",
                        runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                    ).run_order_orchestrator(order_orchestrator_request())
                )
        finally:
            thread.join(5)
            listener.close()

        assert "not the domain's" in str(excinfo.value)

    def test_a_success_body_that_is_not_the_workflows_result_is_an_infra_error(self) -> None:
        for answer in (
            b'{"order_id": "o1"}',
            b'{"order_id": "o1", "total_cents": -5}',
            b"<html>gateway</html>",
            b"",
        ):
            listener = socket.socket()
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]

            def ingress() -> None:  # tesser:debt TB023
                conn, _ = listener.accept()
                with conn:
                    while b"\r\n\r\n" not in conn.recv(4096):
                        continue
                    conn.sendall(
                        b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: "
                        + str(len(answer)).encode()
                        + b"\r\n\r\n"
                        + answer
                    )

            thread = threading.Thread(target=ingress)
            thread.start()
            try:
                with pytest.raises(ports.EngineUnavailable):
                    asyncio.run(
                        runners.RestateOrderOrchestratorRunner(
                            f"http://127.0.0.1:{port}",
                            runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                        ).run_order_orchestrator(order_orchestrator_request())
                    )
            finally:
                thread.join(5)
                listener.close()

    def test_an_error_body_nested_past_the_decoder_is_an_infra_error(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
            with conn:
                while b"\r\n\r\n" not in conn.recv(4096):
                    continue
                answer = b"[" * 10000 + b"]" * 10000
                conn.sendall(
                    b"HTTP/1.1 404 Not Found\r\ncontent-type: application/json\r\ncontent-length: "
                    + str(len(answer)).encode()
                    + b"\r\n\r\n"
                    + answer
                )

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(ports.EngineUnavailable):
                asyncio.run(
                    runners.RestateOrderOrchestratorRunner(
                        f"http://127.0.0.1:{port}",
                        runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                    ).run_order_orchestrator(order_orchestrator_request())
                )
        finally:
            thread.join(5)
            listener.close()

    def test_a_body_whose_code_disagrees_with_the_status_is_not_the_workflows_own(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
            with conn:
                while b"\r\n\r\n" not in conn.recv(4096):
                    continue
                answer = b'{"code":404,"message":"something upstream said"}'
                conn.sendall(
                    b"HTTP/1.1 422 Unprocessable Entity\r\ncontent-type: application/json\r\ncontent-length: "
                    + str(len(answer)).encode()
                    + b"\r\n\r\n"
                    + answer
                )

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(ports.EngineUnavailable):
                asyncio.run(
                    runners.RestateOrderOrchestratorRunner(
                        f"http://127.0.0.1:{port}",
                        runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                    ).run_order_orchestrator(order_orchestrator_request())
                )
        finally:
            thread.join(5)
            listener.close()

    def test_a_refusal_that_is_not_the_workflows_own_is_an_infra_error(self) -> None:
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def ingress() -> None:  # tesser:debt TB023
            conn, _ = listener.accept()
            with conn:
                while b"\r\n\r\n" not in conn.recv(4096):
                    continue
                answer = b'{"message":"service \'OrderOrchestrator\' not found"}'
                conn.sendall(
                    b"HTTP/1.1 404 Not Found\r\ncontent-type: application/json\r\ncontent-length: "
                    + str(len(answer)).encode()
                    + b"\r\n\r\n"
                    + answer
                )

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(ports.EngineUnavailable):
                asyncio.run(
                    runners.RestateOrderOrchestratorRunner(
                        f"http://127.0.0.1:{port}",
                        runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                    ).run_order_orchestrator(order_orchestrator_request())
                )
        finally:
            thread.join(5)
            listener.close()

    def test_an_unreachable_ingress_is_an_infra_error_when_running(self) -> None:
        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            port = closed.getsockname()[1]

        with pytest.raises(ports.EngineUnavailable):
            asyncio.run(
                runners.RestateOrderOrchestratorRunner(
                    f"http://127.0.0.1:{port}",
                    runtimes.RestateOrderRuntime(FakeOrderingApplicationClient(), FakePurchaseApplicationClient()),
                ).run_order_orchestrator(order_orchestrator_request())
            )
