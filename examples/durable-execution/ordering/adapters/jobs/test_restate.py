from __future__ import annotations

import asyncio
import json
import typing

import tesser.testing as ts
import restate

import ordering.adapters.jobs as jobs
import ordering.application.client as client
import ordering.application.ports as ports


@ts.fake
class FakeOrderingApplicationClient(client.OrderingApplicationClient):

    def quote(self, quote_request: ports.QuoteRequest) -> ports.QuoteResponse:
        return ports.QuoteResponse(cents=250)


@ts.fake
class FakeQuoting(ports.Quoting):

    async def quote(
        self, job_context: ts.JobContext, quote_request: ports.QuoteRequest
    ) -> ports.QuoteResponse:
        return ports.QuoteResponse(cents=250)


class TestRestateActionJobs:

    def test_it_declares_the_actions_service_with_its_one_handler(self) -> None:
        restate_action_jobs = jobs.RestateActionJobs(FakeOrderingApplicationClient())
        assert [(d.name, sorted(d.handlers)) for d in restate_action_jobs.definitions()] == [
            ("OrderingActions", ["quote"])
        ]

    def test_the_quote_job_relays_to_the_actions_it_was_given(self) -> None:
        restate_action_jobs = jobs.RestateActionJobs(FakeOrderingApplicationClient())
        quote_response = asyncio.run(
            restate_action_jobs.quote(
                typing.cast(restate.Context, None), ports.QuoteRequest(sku="gadget")
            )
        )
        assert quote_response.cents == 250


class TestRestateWorkflowJobs:

    def test_it_declares_the_workflow_with_its_run_handler(self) -> None:
        restate_workflow_jobs = jobs.RestateWorkflowJobs(FakeQuoting())
        assert [(d.name, sorted(d.handlers)) for d in restate_workflow_jobs.definitions()] == [
            ("Ordering", ["run"])
        ]


class TestRestateJobContext:

    def test_call_journals_the_step_through_the_invocations_context(self) -> None:
        seen: list[str] = []

        class Journaling:
            async def service_call(
                self,
                tpe: restate.context.HandlerType[ports.QuoteRequest, ports.QuoteResponse],
                arg: ports.QuoteRequest,
            ) -> ports.QuoteResponse:
                seen.append(arg.sku)
                return ports.QuoteResponse(cents=250)

        async def quote(ctx: restate.Context, request: ports.QuoteRequest) -> ports.QuoteResponse:  # tesser:debt TB023
            return ports.QuoteResponse(cents=0)

        restate_job_context = jobs.RestateJobContext(
            typing.cast(restate.Context, Journaling())
        )
        quote_response = asyncio.run(
            restate_job_context.call(quote, ports.QuoteRequest(sku="widget"))
        )
        assert quote_response.cents == 250
        assert seen == ["widget"]


class TestRecordSerde:

    def test_it_round_trips_a_record_through_json(self) -> None:
        record_serde = jobs.RecordSerde(ports.QuoteRequest)
        raw = record_serde.serialize(ports.QuoteRequest(sku="widget"))
        assert json.loads(raw) == {"sku": "widget"}
        back = record_serde.deserialize(raw)
        assert back is not None
        assert vars(back) == {"sku": "widget"}

    def test_an_empty_body_is_no_record(self) -> None:
        record_serde = jobs.RecordSerde(ports.QuoteResponse)
        assert record_serde.serialize(None) == b""
        assert record_serde.deserialize(b"") is None
