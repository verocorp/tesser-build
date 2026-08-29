from __future__ import annotations

import asyncio
import json
import typing

import tesser.testing as ts
import restate

import ordering.adapters.jobs.restate as restate_jobs
import ordering.application.client.order_actions as order_actions_client
import ordering.application.ports.quoting as quoting


@ts.fake
class FakeActions(order_actions_client.Client):

    def quote(self, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        return quoting.QuoteResponse(cents=250)


@ts.fake
class FakeQuoting(quoting.Quoting):

    async def quote(self, job: ts.JobContext, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        return quoting.QuoteResponse(cents=250)


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


class TestRecordSerde:

    def test_it_round_trips_a_record_through_json(self) -> None:
        serde = restate_jobs.RecordSerde(quoting.QuoteRequest)
        raw = serde.serialize(quoting.QuoteRequest(sku="widget"))
        assert json.loads(raw) == {"sku": "widget"}
        back = serde.deserialize(raw)
        assert back is not None
        assert vars(back) == {"sku": "widget"}

    def test_an_empty_body_is_no_record(self) -> None:
        serde = restate_jobs.RecordSerde(quoting.QuoteResponse)
        assert serde.serialize(None) == b""
        assert serde.deserialize(b"") is None
