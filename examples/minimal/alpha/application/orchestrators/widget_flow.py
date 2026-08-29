from __future__ import annotations

import tesser.application as ts

import alpha.application.ports.quoting as quoting
import alpha.domain.widget as widget


class FlowResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class MapToQuoteRequest(ts.Mapper, quoting.QuoteRequest):

    def __init__(self, named: widget.Name) -> None:
        super().__init__(name=str(named))


class MapToFlowResponse(ts.Mapper, FlowResponse):

    def __init__(self, quoted: quoting.QuoteResponse) -> None:
        super().__init__(name=quoted.name)


class WidgetFlow(ts.Orchestrator):

    def __init__(self, job: ts.JobContext, quotes: quoting.Quoting) -> None:
        self._job = job
        self._quotes = quotes

    def run(self, request: quoting.QuoteRequest) -> FlowResponse:
        named = widget.Name(request.name)
        quoted = self._quotes.quote(self._job, MapToQuoteRequest(named))
        return MapToFlowResponse(quoted)
