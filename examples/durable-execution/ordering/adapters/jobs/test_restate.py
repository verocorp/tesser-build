from __future__ import annotations

import asyncio
import socket
import threading
import typing

import tesser.testing as ts
import pytest
import restate

import ordering.adapters.jobs.restate as restate_jobs
import ordering.application.client.order_actions as order_actions_client
import ordering.application.relays.order_relay as order_relay
import ordering.domain.order as order
import tesser.errors as errors


@ts.fake
class FakeActions(order_actions_client.Client):

    def quote(self, request: order_relay.QuoteRequest) -> order_relay.QuoteResponse:
        return order_relay.QuoteResponse(cents=250)


@ts.helper
def start_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> order_relay.StartRequest:
    return order_relay.StartRequest(
        order=order.Order(order.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestRestateActionJobs:

    def test_it_declares_the_actions_service_with_its_one_handler(self) -> None:
        jobs = restate_jobs.RestateActionJobs(FakeActions())
        assert [(d.name, sorted(d.handlers)) for d in jobs.definitions()] == [("OrderingActions", ["quote"])]

    def test_the_quote_job_relays_to_the_actions_it_was_given(self) -> None:
        jobs = restate_jobs.RestateActionJobs(FakeActions())
        quoted = asyncio.run(
            jobs.quote(typing.cast(restate.Context, None), order_relay.QuoteRequest(sku="gadget"))
        )
        assert quoted.cents == 250


class TestRestateWorkflowJobs:

    def test_it_declares_the_workflow_with_its_run_handler(self) -> None:
        actions = restate_jobs.RestateActionJobs(FakeActions())
        jobs = restate_jobs.RestateWorkflowJobs("http://127.0.0.1:8080", actions.quote)
        assert [(d.name, sorted(d.handlers)) for d in jobs.definitions()] == [("Ordering", ["run"])]


class TestRestateSerdes:

    def test_the_start_request_shim_carries_the_orders_snapshot(self) -> None:
        serde = restate_jobs.RestateStartRequestSerde()
        raw = serde.serialize(start_request())
        assert raw == b'{"order_id": "o1", "sku": "widget", "quantity": 2}'
        back = serde.deserialize(raw)
        assert back is not None
        assert back.order.sku == order.Sku("widget")

    def test_the_quote_shims_round_trip_their_primitives(self) -> None:
        asked = restate_jobs.RestateQuoteRequestSerde()
        answered = restate_jobs.RestateQuoteResponseSerde()
        assert asked.deserialize(asked.serialize(order_relay.QuoteRequest(sku="widget"))) == order_relay.QuoteRequest(sku="widget")
        assert answered.deserialize(answered.serialize(order_relay.QuoteResponse(cents=250))) == order_relay.QuoteResponse(cents=250)

    def test_an_empty_body_is_no_message(self) -> None:
        assert restate_jobs.RestateStartRequestSerde().serialize(None) == b""
        assert restate_jobs.RestateStartRequestSerde().deserialize(b"") is None
        assert restate_jobs.RestateRunResponseSerde().serialize(None) == b""
        assert restate_jobs.RestateRunResponseSerde().deserialize(b"") is None


class TestRestateOrderRelay:

    def test_starting_sends_the_workflow_keyed_by_the_orders_id(self) -> None:
        actions = restate_jobs.RestateActionJobs(FakeActions())
        jobs = restate_jobs.RestateWorkflowJobs("http://127.0.0.1:1", actions.quote)

        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        seen: list[bytes] = []

        def ingress() -> None:
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

        async def start() -> order_relay.StartResponse:
            relay = restate_jobs.RestateOrderRelay(
                f"http://127.0.0.1:{port}", jobs.run, actions.quote, None
            )
            return await relay.start(start_request())

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            started = asyncio.run(start())
        finally:
            thread.join(5)
            listener.close()

        assert started.order_id == "o1"
        assert seen[0].split(b"\r\n")[0] == b"POST /Ordering/o1/run/send HTTP/1.1"

    def test_a_refused_send_is_an_infra_error(self) -> None:
        actions = restate_jobs.RestateActionJobs(FakeActions())
        jobs = restate_jobs.RestateWorkflowJobs("http://127.0.0.1:1", actions.quote)

        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def ingress() -> None:
            conn, _ = listener.accept()
            with conn:
                while b"\r\n\r\n" not in conn.recv(4096):
                    continue
                conn.sendall(b"HTTP/1.1 404 Not Found\r\ncontent-length: 0\r\n\r\n")

        async def start() -> order_relay.StartResponse:
            relay = restate_jobs.RestateOrderRelay(
                f"http://127.0.0.1:{port}", jobs.run, actions.quote, None
            )
            return await relay.start(start_request())

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(errors.InfraError):
                asyncio.run(start())
        finally:
            thread.join(5)
            listener.close()

    def test_an_unreachable_ingress_is_an_infra_error(self) -> None:
        actions = restate_jobs.RestateActionJobs(FakeActions())
        jobs = restate_jobs.RestateWorkflowJobs("http://127.0.0.1:1", actions.quote)

        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            port = closed.getsockname()[1]

        async def start() -> order_relay.StartResponse:
            relay = restate_jobs.RestateOrderRelay(
                f"http://127.0.0.1:{port}", jobs.run, actions.quote, None
            )
            return await relay.start(start_request())

        with pytest.raises(errors.InfraError):
            asyncio.run(start())

    def test_a_quote_outside_an_invocation_is_an_infra_error(self) -> None:
        actions = restate_jobs.RestateActionJobs(FakeActions())
        jobs = restate_jobs.RestateWorkflowJobs("http://127.0.0.1:1", actions.quote)
        relay = restate_jobs.RestateOrderRelay(
            "http://127.0.0.1:1", jobs.run, actions.quote, None
        )
        with pytest.raises(errors.InfraError):
            asyncio.run(relay.quote(order_relay.QuoteRequest(sku="widget")))
