from __future__ import annotations

import asyncio
import json
import typing

import tesser.testing as ts
import restate

import ordering.adapters.jobs.restate as restate_jobs
import ordering.application.client.order_actions as order_actions_client
import ordering.application.relays.order_workflow as order_workflow
import ordering.application.relays.quoting as quoting
import ordering.domain.order as order


@ts.fake
class FakeActions(order_actions_client.Client):

    def quote(self, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        return quoting.QuoteResponse(cents=250)


@ts.fake
class FakeQuoting(quoting.Quoting):

    async def quote(self, job: ts.JobContext, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        return quoting.QuoteResponse(cents=250)


@ts.helper
def start_request(
    order_id: str = "o1", sku: str = "widget", quantity: int = 2
) -> order_workflow.StartRequest:
    return order_workflow.StartRequest(
        order=order.Order(order.OrderSpec(order_id=order_id, sku=sku, quantity=quantity))
    )


class TestRestateActionJobs:

    def test_it_declares_the_actions_service_with_its_one_handler(self) -> None:
        jobs = restate_jobs.RestateActionJobs(FakeActions())
        assert [(d.name, sorted(d.handlers)) for d in jobs.definitions()] == [("OrderingActions", ["quote"])]

    def test_the_quote_job_relays_to_the_actions_it_was_given(self) -> None:
        jobs = restate_jobs.RestateActionJobs(FakeActions())
        quoted = asyncio.run(
            jobs.quote(typing.cast(restate.Context, None), quoting.QuoteRequest(sku="gadget"))
        )
        assert quoted.cents == 250


class TestRestateWorkflowJobs:

    def test_it_declares_the_workflow_with_its_run_handler(self) -> None:
        jobs = restate_jobs.RestateWorkflowJobs(FakeQuoting())
        assert [(d.name, sorted(d.handlers)) for d in jobs.definitions()] == [("Ordering", ["run"])]


class TestSnapshot:

    def test_it_round_trips_a_flat_record_through_json(self) -> None:
        serde = restate_jobs.Snapshot(quoting.QuoteRequest)
        raw = serde.serialize(quoting.QuoteRequest(sku="widget"))
        assert json.loads(raw) == {"sku": "widget"}
        back = serde.deserialize(raw)
        assert back is not None
        assert vars(back) == {"sku": "widget"}

    def test_it_snapshots_a_relay_message_down_to_json_primitives(self) -> None:
        raw = restate_jobs.Snapshot(order_workflow.StartRequest).serialize(start_request())
        assert json.loads(raw) == {
            "order": {"_id": {"_value": "o1"}, "_sku": {"_value": "widget"}, "_quantity": {"_value": 2}}
        }

    def test_a_relay_message_comes_back_whole_with_its_domain_object(self) -> None:
        serde = restate_jobs.Snapshot(order_workflow.StartRequest)
        back = serde.deserialize(serde.serialize(start_request(order_id="o7", sku="gadget", quantity=3)))
        assert back is not None
        hydrated = back.order
        assert isinstance(hydrated, order.Order)
        assert (str(hydrated.identity), str(hydrated.sku), int(hydrated.quantity)) == ("o7", "gadget", 3)

    def test_a_hydrated_value_object_equals_the_one_it_was_built_from(self) -> None:
        serde = restate_jobs.Snapshot(order_workflow.StartRequest)
        back = serde.deserialize(serde.serialize(start_request()))
        assert back is not None
        assert back.order.sku == order.Sku("widget")
        assert back.order.quantity == order.Quantity(2)
        assert back.order.identity == order.OrderId("o1")

    def test_an_empty_body_is_no_record(self) -> None:
        serde = restate_jobs.Snapshot(quoting.QuoteResponse)
        assert serde.serialize(None) == b""
        assert serde.deserialize(b"") is None
