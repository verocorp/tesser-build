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

    def __init__(self, name: domain.Name, standing: domain.Standing) -> None:
        super().__init__(name=str(name), standing=str(standing))


class MapToAddPartResponse(ts.Mapper, client.AddPartResponse):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(name=str(widget.identity), standing=str(widget.standing))


class MapToRegisterWidgetRequest(ts.Mapper, relays.RegisterWidgetRequest):

    def __init__(self, name: domain.Name) -> None:
        super().__init__(name=str(name))


class MapToCreateWidgetResponse(ts.Mapper, client.CreateWidgetResponse):

    def __init__(self, start_register_widget_response: relays.StartRegisterWidgetResponse) -> None:
        super().__init__(name=start_register_widget_response.name)


class MapToApproveWidgetRequest(ts.Mapper, relays.ApproveWidgetRequest):

    def __init__(self, name: domain.Name) -> None:
        super().__init__(name=str(name))


class MapToApproveWidgetResponse(ts.Mapper, client.ApproveWidgetResponse):

    def __init__(self, approve_widget_response: relays.ApproveWidgetResponse) -> None:
        super().__init__(name=approve_widget_response.name)


class AlphaService(ts.ApplicationService):

    def __init__(
        self,
        widget_repository: ports.WidgetRepository,
        beta_check: ports.BetaCheck,
        widget_orchestrator_relay: relays.WidgetOrchestratorRelay,
    ) -> None:
        self._widget_repository = widget_repository
        self._beta_check = beta_check
        self._widget_orchestrator_relay = widget_orchestrator_relay

    def add_part(self, add_part_request: client.AddPartRequest) -> client.AddPartResponse:
        try:
            widget = domain.Widget(MapToWidgetSpec(add_part_request))
            taken = widget.take(MapToPartSpec(add_part_request))
        except errors.DomainError as domain_error:
            raise client.WidgetRejected(domain_error.code, domain_error.message) from domain_error
        match taken:
            case domain.Taken.TAKEN:
                pass
            case domain.Taken.HELD:
                check_name_response = self._beta_check.check_name(MapToCheckNameRequest(widget))
                widget.clear(MapToClearanceSpec(check_name_response))
            case _ as never:
                typing.assert_never(never)
        self._widget_repository.save_widget(MapToSaveWidgetRequest(widget.identity, widget.standing))
        return MapToAddPartResponse(widget)

    async def create_widget(self, create_widget_request: client.CreateWidgetRequest) -> client.CreateWidgetResponse:
        try:
            name = domain.Name(create_widget_request.name)
        except errors.DomainError as domain_error:
            raise client.WidgetRejected(domain_error.code, domain_error.message) from domain_error
        start_register_widget_response = await self._widget_orchestrator_relay.start_register_widget(
            MapToRegisterWidgetRequest(name)
        )
        return MapToCreateWidgetResponse(start_register_widget_response)

    async def approve_widget(self, approve_widget_request: client.ApproveWidgetRequest) -> client.ApproveWidgetResponse:
        try:
            name = domain.Name(approve_widget_request.name)
        except errors.DomainError as domain_error:
            raise client.WidgetRejected(domain_error.code, domain_error.message) from domain_error
        approve_widget_response = await self._widget_orchestrator_relay.run_approve_widget(MapToApproveWidgetRequest(name))
        return MapToApproveWidgetResponse(approve_widget_response)
