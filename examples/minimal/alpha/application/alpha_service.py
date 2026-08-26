from __future__ import annotations

import tesser.application as ts

import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.widget_repository as widget_repository
import alpha.client.client as client
import alpha.domain.widget as widget


class MapToAddResponse(ts.Mapper, client.AddResponse):

    def __init__(self, added: widget.Widget) -> None:
        super().__init__(name=str(added.identity))


class AlphaService(ts.ApplicationService):

    def __init__(self, widgets: widget_repository.WidgetRepository, checks: beta_check.BetaCheck) -> None:
        self._widgets = widgets
        self._checks = checks

    def add(self, request: client.AddRequest) -> client.AddResponse:
        added = widget.Widget(widget.WidgetSpec(name=request.name, part=widget.PartSpec(id=request.name)))
        added_name = str(added.identity)
        self._checks.check(beta_check.CheckRequest(name=added_name))
        self._widgets.save(widget_repository.SaveRequest(name=added_name))
        return MapToAddResponse(added=added)
