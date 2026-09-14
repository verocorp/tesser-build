from __future__ import annotations

import tesser.application as ts

import alpha.application.ports as ports
import alpha.application.relays as relays
import alpha.domain as domain


class MapToSaveWidgetRequest(ts.Mapper, ports.SaveWidgetRequest):

    def __init__(self, name: domain.Name) -> None:
        super().__init__(name=str(name), standing="kept")


class MapToQuoteWidgetResponse(ts.Mapper, relays.QuoteWidgetResponse):

    def __init__(self, save_widget_response: ports.SaveWidgetResponse) -> None:
        super().__init__(name=save_widget_response.name)


class WidgetActions(ts.Actions):

    def __init__(self, widget_repository: ports.WidgetRepository) -> None:
        self._widget_repository = widget_repository

    def quote_widget(self, quote_widget_request: relays.QuoteWidgetRequest) -> relays.QuoteWidgetResponse:
        name = domain.Name(quote_widget_request.name)
        save_widget_response = self._widget_repository.save_widget(MapToSaveWidgetRequest(name))
        return MapToQuoteWidgetResponse(save_widget_response)
