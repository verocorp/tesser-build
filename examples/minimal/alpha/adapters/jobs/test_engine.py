from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.jobs.engine as engine
import alpha.application.client.widget_actions as widget_actions_client
import alpha.application.ports.widget_actions as widget_actions


@ts.fake
class FakeActionsClient(widget_actions_client.Client):

    def quote(self, request: widget_actions.QuoteRequest) -> widget_actions.QuoteResponse:
        return widget_actions.QuoteResponse(name=request.name)


@ts.fake
class FakeWidgetActions(widget_actions.WidgetActions):

    def quote(self, request: widget_actions.QuoteRequest) -> widget_actions.QuoteResponse:
        return widget_actions.QuoteResponse(name=request.name)


class TestEngineJob:

    def test_the_job_relays_a_quote_to_its_actions(self) -> None:
        job = engine.EngineJob(FakeActionsClient(), FakeWidgetActions())
        quoted = job.quote(widget_actions.QuoteRequest(name="a"))
        assert quoted.name == "a"

    def test_the_job_builds_the_orchestrator_it_runs(self) -> None:
        job = engine.EngineJob(FakeActionsClient(), FakeWidgetActions())
        ran = job.flow(widget_actions.QuoteRequest(name="a"))
        assert ran.name == "a"
