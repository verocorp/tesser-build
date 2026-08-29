from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.jobs.engine as engine
import alpha.application.client.widget_actions as widget_actions_client
import alpha.application.ports.quoting as quoting


@ts.fake
class FakeActionsClient(widget_actions_client.Client):

    def quote(self, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        return quoting.QuoteResponse(name=request.name)


@ts.fake
class FakeQuoting(quoting.Quoting):

    def quote(self, job: ts.JobContext, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        return quoting.QuoteResponse(name=request.name)


class TestEngineJob:

    def test_the_job_relays_a_quote_to_its_actions(self) -> None:
        job = engine.EngineJob(FakeActionsClient(), FakeQuoting())
        quoted = job.quote(quoting.QuoteRequest(name="a"))
        assert quoted.name == "a"

    def test_the_job_builds_the_orchestrator_it_runs(self) -> None:
        job = engine.EngineJob(FakeActionsClient(), FakeQuoting())
        ran = job.flow(quoting.QuoteRequest(name="a"))
        assert ran.name == "a"
