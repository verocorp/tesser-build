from __future__ import annotations

import collections.abc as abc
import typing

import tesser.testing as ts

import alpha.application.orchestrators.widget_flow as widget_flow
import alpha.application.ports.quoting as quoting


@ts.fake
class FakeJobContext(ts.JobContext):

    async def call[I, O](
        self, step: abc.Callable[[typing.Any, I], abc.Awaitable[O]], request: I
    ) -> O:
        return await step(None, request)


@ts.fake
class FakeQuoting(quoting.Quoting):

    def __init__(self) -> None:
        self.quoted: list[str] = []

    def quote(self, job: ts.JobContext, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        self.quoted.append(request.name)
        return quoting.QuoteResponse(name=request.name)


class TestWidgetFlow:

    def test_the_flow_answers_what_the_action_quoted(self) -> None:
        ran = widget_flow.WidgetFlow(FakeJobContext(), FakeQuoting()).run(
            quoting.QuoteRequest(name="a")
        )
        assert ran.name == "a"
