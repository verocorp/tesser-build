from __future__ import annotations

import asyncio
import json
import socket
import threading

import pytest
import restate
import restate.serde

import ordering.adapters.gateways.restate_workflow as restate_workflow
import ordering.application.ports.order_workflow as order_workflow
import protocol.durable as durable
import tesser.errors as errors


class TestRestateOrderWorkflow:

    def test_starting_sends_the_order_to_the_workflow_keyed_by_its_id(self) -> None:
        workflow = restate.Workflow("Ordering")

        @workflow.main(
            input_serde=restate.serde.DefaultSerde(durable.RunRequest),
            output_serde=restate.serde.DefaultSerde(durable.RunResponse),
        )
        async def run(ctx: restate.WorkflowContext, request: durable.RunRequest) -> durable.RunResponse:
            return durable.RunResponse(order_id=ctx.key(), total_cents=0)

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

        async def start() -> order_workflow.StartResponse:
            workflows = restate_workflow.RestateOrderWorkflow(f"http://127.0.0.1:{port}", run)
            return await workflows.start(order_workflow.StartRequest(order_id="o1", sku="widget", quantity=2))

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            started = asyncio.run(start())
        finally:
            thread.join(5)
            listener.close()

        assert started.order_id == "o1"
        assert seen[0].split(b"\r\n")[0] == b"POST /Ordering/o1/run/send HTTP/1.1"
        assert json.loads(seen[1]) == {"sku": "widget", "quantity": 2}

    def test_a_refused_send_is_an_infra_error(self) -> None:
        workflow = restate.Workflow("Ordering")

        @workflow.main(
            input_serde=restate.serde.DefaultSerde(durable.RunRequest),
            output_serde=restate.serde.DefaultSerde(durable.RunResponse),
        )
        async def run(ctx: restate.WorkflowContext, request: durable.RunRequest) -> durable.RunResponse:
            return durable.RunResponse(order_id=ctx.key(), total_cents=0)

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

        async def start() -> order_workflow.StartResponse:
            workflows = restate_workflow.RestateOrderWorkflow(f"http://127.0.0.1:{port}", run)
            return await workflows.start(order_workflow.StartRequest(order_id="o1", sku="widget", quantity=2))

        thread = threading.Thread(target=ingress)
        thread.start()
        try:
            with pytest.raises(errors.InfraError):
                asyncio.run(start())
        finally:
            thread.join(5)
            listener.close()

    def test_an_unreachable_ingress_is_an_infra_error(self) -> None:
        workflow = restate.Workflow("Ordering")

        @workflow.main(
            input_serde=restate.serde.DefaultSerde(durable.RunRequest),
            output_serde=restate.serde.DefaultSerde(durable.RunResponse),
        )
        async def run(ctx: restate.WorkflowContext, request: durable.RunRequest) -> durable.RunResponse:
            return durable.RunResponse(order_id=ctx.key(), total_cents=0)

        with socket.socket() as closed:
            closed.bind(("127.0.0.1", 0))
            port = closed.getsockname()[1]

        async def start() -> order_workflow.StartResponse:
            workflows = restate_workflow.RestateOrderWorkflow(f"http://127.0.0.1:{port}", run)
            return await workflows.start(order_workflow.StartRequest(order_id="o1", sku="widget", quantity=2))

        with pytest.raises(errors.InfraError):
            asyncio.run(start())
