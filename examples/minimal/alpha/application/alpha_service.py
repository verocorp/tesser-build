from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.ports as ports
import alpha.application.relays as relays
import alpha.client as client
import alpha.domain as domain
import tesser.errors as errors


class MapToWidgetSpec(ts.Mapper, domain.WidgetSpec):

    def __init__(self, add_part_request: client.AddPartRequest) -> None:
        super().__init__(name=add_part_request.name, part=domain.PartSpec(id=add_part_request.name), standing="kept")


class MapToPartSpec(ts.Mapper, domain.PartSpec):

    def __init__(self, add_part_request: client.AddPartRequest) -> None:
        super().__init__(id=add_part_request.part)


class MapToCheckNameRequest(ts.Mapper, ports.CheckNameRequest):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(name=str(widget.identity))


class MapToClearanceSpec(ts.Mapper, domain.ClearanceSpec):

    def __init__(self, check_name_response: ports.CheckNameResponse) -> None:
        super().__init__(verdict=check_name_response.outcome.value)


class MapToSaveWidgetRequest(ts.Mapper, ports.SaveWidgetRequest):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(name=str(widget.identity), standing=str(widget.standing))


class MapToAddPartResponse(ts.Mapper, client.AddPartResponse):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(name=str(widget.identity), standing=str(widget.standing))


class MapToRegisterWidgetRequest(ts.Mapper, relays.RegisterWidgetRequest):

    def __init__(self, create_widget_request: client.CreateWidgetRequest) -> None:
        super().__init__(name=create_widget_request.name)


class MapToCreateWidgetResponse(ts.Mapper, client.CreateWidgetResponse):

    def __init__(self, register_widget_response: relays.RegisterWidgetResponse) -> None:
        super().__init__(name=register_widget_response.name)


class AlphaService(ts.ApplicationService):

    def __init__(
        self,
        widget_repository: ports.WidgetRepository,
        beta_check: ports.BetaCheck,
        register_widget_relay: relays.RegisterWidgetRelay,
    ) -> None:
        self._widget_repository = widget_repository
        self._beta_check = beta_check
        self._register_widget_relay = register_widget_relay

    def add_part(self, add_part_request: client.AddPartRequest) -> client.AddPartResponse:
        try:
            widget = domain.Widget(MapToWidgetSpec(add_part_request))
            taken = widget.take(MapToPartSpec(add_part_request))
        except errors.DomainError as domain_error:
            raise client.Rejected(domain_error.code, domain_error.message) from domain_error
        match taken:
            case domain.Taken.TAKEN:
                pass
            case domain.Taken.HELD:
                check_name_response = self._beta_check.check_name(MapToCheckNameRequest(widget))
                widget.clear(MapToClearanceSpec(check_name_response))
            case _ as never:
                typing.assert_never(never)
        self._widget_repository.save_widget(MapToSaveWidgetRequest(widget))
        return MapToAddPartResponse(widget)

    def create_widget(self, create_widget_request: client.CreateWidgetRequest) -> client.CreateWidgetResponse:
        register_widget_response = self._register_widget_relay.run_register_widget(
            MapToRegisterWidgetRequest(create_widget_request)
        )
        return MapToCreateWidgetResponse(register_widget_response)
