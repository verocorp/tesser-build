from __future__ import annotations

import asyncio
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


class TestRestateJobs:

    def test_it_declares_one_workflow_and_one_service(self) -> None:
        jobs = restate_jobs.RestateJobs(FakeActions())
        assert [d.name for d in jobs.definitions()] == ["Ordering", "OrderingActions"]

    def test_each_definition_carries_the_handler_named_for_its_function(self) -> None:
        jobs = restate_jobs.RestateJobs(FakeActions())
        assert [sorted(d.handlers) for d in jobs.definitions()] == [["run"], ["quote"]]

    def test_the_quote_job_relays_to_the_actions_it_was_given(self) -> None:
        jobs = restate_jobs.RestateJobs(FakeActions())
        quoted = asyncio.run(
            jobs.quote(typing.cast(restate.Context, None), quoting.QuoteRequest(sku="gadget"))
        )
        assert quoted.cents == 250
