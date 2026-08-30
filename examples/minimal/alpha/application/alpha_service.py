from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.widget_repository as widget_repository
import alpha.client.client as client
import alpha.domain.clearance as clearance
import alpha.domain.widget as widget


class MapToWidgetSpec(ts.Mapper, widget.WidgetSpec):

    def __init__(self, request: client.AddRequest) -> None:
        super().__init__(name=request.name, part=widget.PartSpec(id=request.name), standing="kept")


class MapToPartSpec(ts.Mapper, widget.PartSpec):

    def __init__(self, request: client.AddRequest) -> None:
        super().__init__(id=request.part)


class MapToCheckRequest(ts.Mapper, beta_check.CheckRequest):

    def __init__(self, added: widget.Widget) -> None:
        super().__init__(name=str(added.identity))


class MapToClearanceSpec(ts.Mapper, clearance.ClearanceSpec):

    def __init__(self, answer: beta_check.CheckResponse) -> None:
        super().__init__(verdict=answer.verdict.value)


class MapToSaveRequest(ts.Mapper, widget_repository.SaveRequest):

    def __init__(self, added: widget.Widget) -> None:
        super().__init__(name=str(added.identity), standing=str(added.standing))


class MapToAddResponse(ts.Mapper, client.AddResponse):

    def __init__(self, added: widget.Widget) -> None:
        super().__init__(name=str(added.identity), standing=str(added.standing))


class AlphaService(ts.ApplicationService):

    def __init__(self, widgets: widget_repository.WidgetRepository, checks: beta_check.BetaCheck) -> None:
        self._widgets = widgets
        self._checks = checks

    def add(self, request: client.AddRequest) -> client.AddResponse:
        added = widget.Widget(MapToWidgetSpec(request))
        match added.take(MapToPartSpec(request)):
            case widget.Taken.TAKEN:
                pass
            case widget.Taken.HELD:
                answer = self._checks.check(MapToCheckRequest(added))
                added.clear(MapToClearanceSpec(answer))
            case _ as never:
                typing.assert_never(never)
        self._widgets.save(MapToSaveRequest(added))
        return MapToAddResponse(added)
