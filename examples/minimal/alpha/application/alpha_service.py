from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.ports as ports
import alpha.client as client
import alpha.domain as domain
import tesser.errors as errors


class MapToWidgetSpec(ts.Mapper, domain.WidgetSpec):

    def __init__(self, add_request: client.AddRequest) -> None:
        super().__init__(name=add_request.name, part=domain.PartSpec(id=add_request.name), standing="kept")


class MapToPartSpec(ts.Mapper, domain.PartSpec):

    def __init__(self, add_request: client.AddRequest) -> None:
        super().__init__(id=add_request.part)


class MapToCheckRequest(ts.Mapper, ports.CheckRequest):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(name=str(widget.identity))


class MapToClearanceSpec(ts.Mapper, domain.ClearanceSpec):

    def __init__(self, check_response: ports.CheckResponse) -> None:
        super().__init__(verdict=check_response.verdict.value)


class MapToSaveRequest(ts.Mapper, ports.SaveRequest):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(name=str(widget.identity), standing=str(widget.standing))


class MapToAddResponse(ts.Mapper, client.AddResponse):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(name=str(widget.identity), standing=str(widget.standing))


class AlphaService(ts.ApplicationService):

    def __init__(self, widget_repository: ports.WidgetRepository, beta_check: ports.BetaCheck) -> None:
        self._widget_repository = widget_repository
        self._beta_check = beta_check

    def add(self, add_request: client.AddRequest) -> client.AddResponse:
        try:
            widget = domain.Widget(MapToWidgetSpec(add_request))
            taken = widget.take(MapToPartSpec(add_request))
        except errors.DomainError as domain_error:
            raise client.Rejected(domain_error.code, domain_error.message) from domain_error
        match taken:
            case domain.Taken.TAKEN:
                pass
            case domain.Taken.HELD:
                check_response = self._beta_check.check(MapToCheckRequest(widget))
                widget.clear(MapToClearanceSpec(check_response))
            case _ as never:
                typing.assert_never(never)
        self._widget_repository.save(MapToSaveRequest(widget))
        return MapToAddResponse(widget)
