from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.jobs.engine as engine
import alpha.application.client as client
import alpha.application.ports as ports


@ts.fake
class FakeActionsClient(client.Client):

    def quote(self, quote_request: ports.QuoteRequest) -> ports.QuoteResponse:
        return ports.QuoteResponse(name=quote_request.name)


@ts.fake
class FakeQuoting(ports.Quoting):

    def quote(self, job_context: ts.JobContext, quote_request: ports.QuoteRequest) -> ports.QuoteResponse:
        return ports.QuoteResponse(name=quote_request.name)


class TestEngineJob:

    def test_the_job_relays_a_quote_to_its_actions(self) -> None:
        engine_job = engine.EngineJob(FakeActionsClient(), FakeQuoting())
        quoted = engine_job.quote(ports.QuoteRequest(name="a"))
        assert quoted.name == "a"

    def test_the_job_builds_the_orchestrator_it_runs(self) -> None:
        engine_job = engine.EngineJob(FakeActionsClient(), FakeQuoting())
        ran = engine_job.flow(ports.QuoteRequest(name="a"))
        assert ran.name == "a"
