from __future__ import annotations

import asyncio
import socket
import threading

import tesser.testing as ts
import httpx
import pytest
import restate

import ordering.adapters.runners as runners
import ordering.adapters.runtimes as runtimes
import ordering.application.client as client
import ordering.application.relays as relays
import ordering.domain as domain


@ts.fake
class FakeOrderingApplicationClient(client.OrderingApplicationClient):

    def price_product(
        self, price_product_request: relays.PriceProductRequest
    ) -> relays.PriceProductResponse:
        return relays.PriceProductResponse(
            outcome=relays.PriceProductOutcome.PRICED,
            prices=(relays.Price(cents=250),),
            reasons=(),
        )


@ts.fake
class FakePurchaseApplicationClient(client.PurchaseApplicationClient):

    def take_payment(
        self, take_payment_request: relays.TakePaymentRequest
    ) -> relays.TakePaymentResponse:
        return relays.TakePaymentResponse(
            outcome=relays.TakePaymentOutcome.TAKEN,
            order_id=take_payment_request.order_id,
            payments=(
                relays.Payment(
                    reference=f"pay-{take_payment_request.order_id}",
                    cents=take_payment_request.cents,
                ),
            ),
            reasons=(),
        )


@ts.fake
class FakeRestateIngress:  # tesser:debt TB072

    def __init__(self, answer: bytes, status_line: bytes = b"HTTP/1.1 200 OK") -> None:
        self._answer = answer
        self._status_line = status_line
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
                self._status_line
                + b"\r\ncontent-type: application/json\r\ncontent-length: "
                + str(len(self._answer)).encode()
                + b"\r\n\r\n"
                + self._answer
            )

    def close(self) -> None:
        self._thread.join(5)
        self._listener.close()


@ts.helper
def confirm_order_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> relays.ConfirmOrderRequest:
    return relays.ConfirmOrderRequest(
        order=domain.Order(domain.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


@ts.helper
def restate_order_runtime() -> runtimes.RestateOrderRuntime:  # tesser:debt TB073
    return runtimes.RestateOrderRuntime(
        FakeOrderingApplicationClient(), FakePurchaseApplicationClient()
    )


@ts.helper
def accepted() -> bytes:  # tesser:debt TB073
    return b'{"invocationId": "inv_1", "status": "Accepted"}'


@ts.helper
def confirmed() -> bytes:  # tesser:debt TB073
    return relays.ConfirmOrderResponseSnapshot().serialize(
        relays.ConfirmOrderResponse(
            outcome=relays.ConfirmOrderOutcome.CONFIRMED,
            order_id="o1",
            confirmed_orders=(relays.ConfirmedOrder(total_cents=500),),
            reasons=(),
        )
    )


@ts.helper
def unreachable_ingress() -> str:  # tesser:debt TB073
    with socket.socket() as closed:
        closed.bind(("127.0.0.1", 0))
        return f"http://127.0.0.1:{closed.getsockname()[1]}"


class TestRestateIngressConfirmOrderRelayStarting:

    def test_starting_sends_the_workflow_keyed_by_the_orders_id(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            accepted(), b"HTTP/1.1 202 Accepted"
        )
        fake_restate_ingress.start()
        try:
            start_confirm_order_response = asyncio.run(
                runners.RestateIngressConfirmOrderRelay(
                    fake_restate_ingress.base_url, restate_order_runtime()
                ).start_confirm_order(confirm_order_request())
            )
        finally:
            fake_restate_ingress.close()
        assert (
            start_confirm_order_response.outcome is relays.StartConfirmOrderOutcome.STARTED
        )
        assert start_confirm_order_response.order_id == "o1"
        assert fake_restate_ingress.seen[0].split(b"\r\n")[0] == (
            b"POST /OrderOrchestrator/o1/confirm_order/send HTTP/1.1"
        )
        assert fake_restate_ingress.seen[1] == relays.ConfirmOrderRequestSnapshot().serialize(
            confirm_order_request()
        )

    def test_the_key_is_encoded_so_an_order_id_cannot_reshape_the_path(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            accepted(), b"HTTP/1.1 202 Accepted"
        )
        fake_restate_ingress.start()
        try:
            start_confirm_order_response = asyncio.run(
                runners.RestateIngressConfirmOrderRelay(
                    fake_restate_ingress.base_url, restate_order_runtime()
                ).start_confirm_order(confirm_order_request(order_id="../admin?x=1#f"))
            )
        finally:
            fake_restate_ingress.close()
        assert start_confirm_order_response.order_id == "../admin?x=1#f"
        assert fake_restate_ingress.seen[0].split(b"\r\n")[0] == (
            b"POST /OrderOrchestrator/..%2Fadmin%3Fx%3D1%23f/confirm_order/send HTTP/1.1"
        )

    def test_a_refused_send_is_a_fault_because_a_repeat_send_is_deduplicated(self) -> None:
        fake_restate_ingress = FakeRestateIngress(b"", b"HTTP/1.1 409 Conflict")  # tesser:debt TB085
        fake_restate_ingress.start()
        try:
            with pytest.raises(restate.HttpError):
                asyncio.run(
                    runners.RestateIngressConfirmOrderRelay(
                        fake_restate_ingress.base_url, restate_order_runtime()
                    ).start_confirm_order(confirm_order_request())
                )
        finally:
            fake_restate_ingress.close()

    def test_an_unreachable_ingress_is_a_fault(self) -> None:
        with pytest.raises(httpx.TransportError):
            asyncio.run(
                runners.RestateIngressConfirmOrderRelay(
                    unreachable_ingress(), restate_order_runtime()
                ).start_confirm_order(confirm_order_request())
            )


class TestRestateIngressConfirmOrderRelayRunning:

    def test_running_calls_the_workflow_and_answers_with_its_result(self) -> None:
        fake_restate_ingress = FakeRestateIngress(confirmed())  # tesser:debt TB085
        fake_restate_ingress.start()
        try:
            confirm_order_response = asyncio.run(
                runners.RestateIngressConfirmOrderRelay(
                    fake_restate_ingress.base_url, restate_order_runtime()
                ).run_confirm_order(confirm_order_request())
            )
        finally:
            fake_restate_ingress.close()
        assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.CONFIRMED
        assert confirm_order_response.order_id == "o1"
        assert confirm_order_response.confirmed_orders[0].total_cents == 500
        assert fake_restate_ingress.seen[0].split(b"\r\n")[0] == (
            b"POST /OrderOrchestrator/o1/confirm_order HTTP/1.1"
        )
        assert fake_restate_ingress.seen[1] == relays.ConfirmOrderRequestSnapshot().serialize(
            confirm_order_request()
        )

    def test_the_already_invoked_conflict_is_the_outcome_the_engine_crossing_adds(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            b'{"code":409,"message":"the workflow method was already invoked"}',
            b"HTTP/1.1 409 Conflict",
        )
        fake_restate_ingress.start()
        try:
            confirm_order_response = asyncio.run(
                runners.RestateIngressConfirmOrderRelay(
                    fake_restate_ingress.base_url, restate_order_runtime()
                ).run_confirm_order(confirm_order_request())
            )
        finally:
            fake_restate_ingress.close()
        assert confirm_order_response.outcome is relays.ConfirmOrderOutcome.ALREADY_STARTED
        assert confirm_order_response.order_id == "o1"
        assert confirm_order_response.confirmed_orders == ()
        assert confirm_order_response.reasons == ()

    def test_a_cancellation_409_is_a_fault_because_only_the_message_tells_it_apart(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            b'{"code":409,"message":"cancelled"}', b"HTTP/1.1 409 Conflict"
        )
        fake_restate_ingress.start()
        try:
            with pytest.raises(restate.HttpError) as excinfo:
                asyncio.run(
                    runners.RestateIngressConfirmOrderRelay(
                        fake_restate_ingress.base_url, restate_order_runtime()
                    ).run_confirm_order(confirm_order_request())
                )
        finally:
            fake_restate_ingress.close()
        assert excinfo.value.status_code == 409

    def test_a_workflow_that_ended_terminally_is_a_fault_at_every_other_status(self) -> None:
        for answer, status_line, status_code in (
            (b'{"code":404,"message":"no price for sku \'nope\'"}', b"HTTP/1.1 404 Not Found", 404),
            (
                b'{"code":422,"message":"an order is for at least one unit"}',
                b"HTTP/1.1 422 Unprocessable Entity",
                422,
            ),
            (
                b'{"code":500,"message":"Unable to parse an input argument"}',
                b"HTTP/1.1 500 Internal Server Error",
                500,
            ),
            (b'{"message":"service not found"}', b"HTTP/1.1 404 Not Found", 404),
        ):
            fake_restate_ingress = FakeRestateIngress(answer, status_line)  # tesser:debt TB085
            fake_restate_ingress.start()
            try:
                with pytest.raises(restate.HttpError) as excinfo:
                    asyncio.run(
                        runners.RestateIngressConfirmOrderRelay(
                            fake_restate_ingress.base_url, restate_order_runtime()
                        ).run_confirm_order(confirm_order_request())
                    )
            finally:
                fake_restate_ingress.close()
            assert excinfo.value.status_code == status_code

    def test_a_success_body_that_is_not_the_workflows_result_is_a_fault(self) -> None:
        for answer in (
            b'{"outcome": "confirmed", "order_id": "o1"}',
            b"<html>gateway</html>",
            b"",
        ):
            fake_restate_ingress = FakeRestateIngress(answer)  # tesser:debt TB085
            fake_restate_ingress.start()
            try:
                with pytest.raises(restate.TerminalError) as excinfo:
                    asyncio.run(
                        runners.RestateIngressConfirmOrderRelay(
                            fake_restate_ingress.base_url, restate_order_runtime()
                        ).run_confirm_order(confirm_order_request())
                    )
            finally:
                fake_restate_ingress.close()
            assert excinfo.value.status_code == 400

    def test_a_conflict_body_that_is_not_json_is_a_fault(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            b"conflict, but not as json", b"HTTP/1.1 409 Conflict"
        )
        fake_restate_ingress.start()
        try:
            with pytest.raises(restate.HttpError):
                asyncio.run(
                    runners.RestateIngressConfirmOrderRelay(
                        fake_restate_ingress.base_url, restate_order_runtime()
                    ).run_confirm_order(confirm_order_request())
                )
        finally:
            fake_restate_ingress.close()

    def test_a_conflict_body_nested_past_the_decoder_is_a_fault(self) -> None:
        fake_restate_ingress = FakeRestateIngress(  # tesser:debt TB085
            b"[" * 10000 + b"]" * 10000, b"HTTP/1.1 409 Conflict"
        )
        fake_restate_ingress.start()
        try:
            with pytest.raises(restate.HttpError):
                asyncio.run(
                    runners.RestateIngressConfirmOrderRelay(
                        fake_restate_ingress.base_url, restate_order_runtime()
                    ).run_confirm_order(confirm_order_request())
                )
        finally:
            fake_restate_ingress.close()

    def test_an_unreachable_ingress_is_a_fault_when_running(self) -> None:
        with pytest.raises(httpx.TransportError):
            asyncio.run(
                runners.RestateIngressConfirmOrderRelay(
                    unreachable_ingress(), restate_order_runtime()
                ).run_confirm_order(confirm_order_request())
            )
