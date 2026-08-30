from __future__ import annotations

import tesser.application as ts

import alpha.application.ports.quoting as quoting
import alpha.application.ports.widget_repository as widget_repository
import alpha.domain.widget as widget


class MapToSaveRequest(ts.Mapper, widget_repository.SaveRequest):

    def __init__(self, named: widget.Name) -> None:
        super().__init__(name=str(named), standing="kept")


class MapToQuoteResponse(ts.Mapper, quoting.QuoteResponse):

    def __init__(self, saved: widget_repository.SaveResponse) -> None:
        super().__init__(name=saved.name)


class WidgetActions(ts.Actions):

    def __init__(self, widgets: widget_repository.WidgetRepository) -> None:
        self._widgets = widgets

    def quote(self, request: quoting.QuoteRequest) -> quoting.QuoteResponse:
        named = widget.Name(request.name)
        saved = self._widgets.save(MapToSaveRequest(named))
        return MapToQuoteResponse(saved)
