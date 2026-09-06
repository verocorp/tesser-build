from __future__ import annotations

import tesser.application as ts

import alpha.application.ports as ports
import alpha.domain as domain


class MapToSaveRequest(ts.Mapper, ports.SaveRequest):

    def __init__(self, name: domain.Name) -> None:
        super().__init__(name=str(name), standing="kept")


class MapToQuoteResponse(ts.Mapper, ports.QuoteResponse):

    def __init__(self, save_response: ports.SaveResponse) -> None:
        super().__init__(name=save_response.name)


class WidgetActions(ts.Actions):

    def __init__(self, widget_repository: ports.WidgetRepository) -> None:
        self._widget_repository = widget_repository

    def quote(self, quote_request: ports.QuoteRequest) -> ports.QuoteResponse:
        name = domain.Name(quote_request.name)
        save_response = self._widget_repository.save(MapToSaveRequest(name))
        return MapToQuoteResponse(save_response)
