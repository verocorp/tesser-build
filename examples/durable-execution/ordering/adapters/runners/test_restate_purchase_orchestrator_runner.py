from __future__ import annotations

import asyncio
import socket
import threading

import tesser.testing as ts
import pytest

import ordering.adapters.runners as runners
import ordering.adapters.runtimes as runtimes
import ordering.application.client as client
import ordering.application.relays as relays
import ordering.domain as domain
import tesser.errors as errors


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
def purchase_orchestrator_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> relays.PurchaseOrchestratorRequest:
    return relays.PurchaseOrchestratorRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestRestatePurchaseOrchestratorRunner:

    def test_running_calls_the_purchase_workflow_keyed_by_the_orders_id_and_answers_its_result(self) -> None:
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
                answer = relays.PurchaseOrchestratorResponseSnapshot().serialize(
                    relays.PurchaseOrchestratorResponse(
                        order_id="o1", total_cents=500, payment_reference="pay-o1"
                    )
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
            purchase_orchestrator_response = asyncio.run(
                runners.RestatePurchaseOrchestratorRunner(
                    f"http://127.0.0.1:{port}",
                    runtimes.RestateOrderRuntime(
                        FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                    ),
                ).run_purchase_orchestrator(purchase_orchestrator_request())
            )
        finally:
            thread.join(5)
            listener.close()

        assert purchase_orchestrator_response == relays.PurchaseOrchestratorResponse(
            order_id="o1", total_cents=500, payment_reference="pay-o1"
        )
        assert seen[0].split(b"\r\n")[0] == b"POST /PurchaseOrchestrator/o1/run HTTP/1.1"
        assert seen[1] == relays.PurchaseOrchestratorRequestSnapshot().serialize(
            purchase_orchestrator_request()
        )

    def test_a_workflow_that_ended_terminally_answers_with_the_domains_own_kind(self) -> None:
        for status_line, answer, kind in (
            (
                b"HTTP/1.1 409 Conflict",
                b'{"code":409,"message":"the workflow method was already invoked"}',
                errors.Kind.CONFLICT,
            ),
            (
                b"HTTP/1.1 404 Not Found",
                b'{"code":404,"message":"no price for sku \'nope\'"}',
                errors.Kind.NOT_FOUND,
            ),
            (
                b"HTTP/1.1 422 Unprocessable Entity",
                b'{"code":422,"message":"an order is for at least one unit"}',
                errors.Kind.VALIDATION,
            ),
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
                        status_line
                        + b"\r\ncontent-type: application/json\r\ncontent-length: "
                        + str(len(answer)).encode()
                        + b"\r\n\r\n"
                        + answer
                    )

            thread = threading.Thread(target=ingress)
            thread.start()
            try:
                with pytest.raises(errors.DomainError) as excinfo:
                    asyncio.run(
                        runners.RestatePurchaseOrchestratorRunner(
                            f"http://127.0.0.1:{port}",
                            runtimes.RestateOrderRuntime(
                                FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                            ),
                        ).run_purchase_orchestrator(purchase_orchestrator_request())
                    )
            finally:
                thread.join(5)
                listener.close()

            assert excinfo.value.kind is kind
            assert excinfo.value.code == "purchase_rejected"
            assert excinfo.value.message.encode() in answer

    def test_a_refusal_that_is_not_the_workflows_is_an_infra_error(self) -> None:
        for status_line, answer in (
            (b"HTTP/1.1 404 Not Found", b'{"message":"service PurchaseOrchestrator not found"}'),
            (b"HTTP/1.1 500 Internal Server Error", b'{"code":500,"message":"Unable to parse"}'),
            (b"HTTP/1.1 409 Conflict", b'{"code":"proxy_error","message":"x"}'),
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
                        status_line
                        + b"\r\ncontent-type: application/json\r\ncontent-length: "
                        + str(len(answer)).encode()
                        + b"\r\n\r\n"
                        + answer
                    )

            thread = threading.Thread(target=ingress)
            thread.start()
            try:
                with pytest.raises(errors.InfraError):
                    asyncio.run(
                        runners.RestatePurchaseOrchestratorRunner(
                            f"http://127.0.0.1:{port}",
                            runtimes.RestateOrderRuntime(
                                FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                            ),
                        ).run_purchase_orchestrator(purchase_orchestrator_request())
                    )
            finally:
                thread.join(5)
                listener.close()

    def test_a_success_body_that_is_not_the_workflows_result_is_an_infra_error(self) -> None:
        for answer in (
            b'{"order_id": "o1", "total_cents": 500}',
            b'{"order_id": "o1", "total_cents": 500, "payment_reference": 7}',
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
                with pytest.raises(errors.InfraError):
                    asyncio.run(
                        runners.RestatePurchaseOrchestratorRunner(
                            f"http://127.0.0.1:{port}",
                            runtimes.RestateOrderRuntime(
                                FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                            ),
                        ).run_purchase_orchestrator(purchase_orchestrator_request())
                    )
            finally:
                thread.join(5)
                listener.close()

    def test_an_unreachable_ingress_is_an_infra_error(self) -> None:
        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            port = closed.getsockname()[1]

        with pytest.raises(errors.InfraError):
            asyncio.run(
                runners.RestatePurchaseOrchestratorRunner(
                    f"http://127.0.0.1:{port}",
                    runtimes.RestateOrderRuntime(
                        FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                    ),
                ).run_purchase_orchestrator(purchase_orchestrator_request())
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
                answer = relays.PurchaseOrchestratorResponseSnapshot().serialize(
                    relays.PurchaseOrchestratorResponse(
                        order_id="../admin?x=1#f", total_cents=500, payment_reference="pay-1"
                    )
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
            purchase_orchestrator_response = asyncio.run(
                runners.RestatePurchaseOrchestratorRunner(
                    f"http://127.0.0.1:{port}",
                    runtimes.RestateOrderRuntime(
                        FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                    ),
                ).run_purchase_orchestrator(purchase_orchestrator_request(order_id="../admin?x=1#f"))
            )
        finally:
            thread.join(5)
            listener.close()

        assert purchase_orchestrator_response.order_id == "../admin?x=1#f"
        assert seen[0].split(b"\r\n")[0] == (
            b"POST /PurchaseOrchestrator/..%2Fadmin%3Fx%3D1%23f/run HTTP/1.1"
        )

    def test_a_success_body_nested_past_the_decoder_is_an_infra_error(self) -> None:
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
                    b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\ncontent-length: "
                    + str(len(answer)).encode()
                    + b"\r\n\r\n"
                    + answer
                )

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(errors.InfraError):
                asyncio.run(
                    runners.RestatePurchaseOrchestratorRunner(
                        f"http://127.0.0.1:{port}",
                        runtimes.RestateOrderRuntime(
                            FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
                        ),
                    ).run_purchase_orchestrator(purchase_orchestrator_request())
                )
        finally:
            thread.join(5)
            listener.close()
