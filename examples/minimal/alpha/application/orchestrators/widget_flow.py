from __future__ import annotations

import tesser.application as ts

import alpha.application.ports as ports
import alpha.domain as domain


class FlowResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class MapToQuoteRequest(ts.Mapper, ports.QuoteRequest):

    def __init__(self, name: domain.Name) -> None:
        super().__init__(name=str(name))


class MapToFlowResponse(ts.Mapper, FlowResponse):

    def __init__(self, quote_response: ports.QuoteResponse) -> None:
        super().__init__(name=quote_response.name)


class WidgetFlow(ts.Orchestrator):

    def __init__(self, job_context: ts.JobContext, quoting: ports.Quoting) -> None:
        self._job_context = job_context
        self._quoting = quoting

    def run(self, quote_request: ports.QuoteRequest) -> FlowResponse:
        name = domain.Name(quote_request.name)
        quote_response = self._quoting.quote(self._job_context, MapToQuoteRequest(name))
        return MapToFlowResponse(quote_response)
