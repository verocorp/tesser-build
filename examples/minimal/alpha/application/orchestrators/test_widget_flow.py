from __future__ import annotations

import collections.abc as abc
import typing

import tesser.testing as ts

import alpha.application.orchestrators as orchestrators
import alpha.application.ports as ports


@ts.fake
class FakeJobContext(ts.JobContext):

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I
    ) -> O:
        return await step(None, request)


@ts.fake
class FakeQuoting(ports.Quoting):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    def quote(self, job_context: ts.JobContext, quote_request: ports.QuoteRequest) -> ports.QuoteResponse:
        self.quoted.append(quote_request.name)
        return ports.QuoteResponse(name=quote_request.name)


class TestWidgetFlow:

    def test_the_flow_answers_what_the_action_quoted(self) -> None:
        flow_response = orchestrators.WidgetFlow(FakeJobContext(), FakeQuoting()).run(
            ports.QuoteRequest(name="a")
        )
        assert flow_response.name == "a"
