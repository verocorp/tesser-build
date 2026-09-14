from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.ports as ports
import alpha.client as client
import alpha.domain as domain
import tesser.errors as errors


class MapToWidgetSpec(ts.Mapper, domain.WidgetSpec):

    def __init__(self, add_part_request: client.AddPartRequest) -> None:
        super().__init__(
            name=add_part_request.name,
            part=domain.PartSpec(id=add_part_request.name),
            standing="kept",
        )


class MapToLoadedWidgetSpec(ts.Mapper, domain.WidgetSpec):

    def __init__(
        self,
        load_widget_request: ports.LoadWidgetRequest,
        load_widget_response: ports.LoadWidgetResponse,
    ) -> None:
        match load_widget_response.outcome:
            case ports.LoadWidgetOutcome.FOUND:
                record = load_widget_response.widgets[0]
            case ports.LoadWidgetOutcome.NOT_FOUND:
                raise client.WidgetNotFound(
                    message=f"no widget {load_widget_request.name!r}"
                )
            case _ as never:
                typing.assert_never(never)
        super().__init__(
            name=record.name,
            part=domain.PartSpec(id=record.part),
            standing=record.standing,
        )


class MapToPartSpec(ts.Mapper, domain.PartSpec):

    def __init__(self, add_part_request: client.AddPartRequest) -> None:
        super().__init__(id=add_part_request.part)


class MapToTakenPartSpec(ts.Mapper, domain.PartSpec):

    def __init__(self, take_part_request: client.TakePartRequest) -> None:
        super().__init__(id=take_part_request.part)


class MapToCheckNameRequest(ts.Mapper, ports.CheckNameRequest):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(name=str(widget.identity))


class MapToClearanceSpec(ts.Mapper, domain.ClearanceSpec):

    def __init__(self, check_name_response: ports.CheckNameResponse) -> None:
        super().__init__(verdict=check_name_response.outcome.value)


class MapToAddWidgetRequest(ts.Mapper, ports.AddWidgetRequest):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(
            name=str(widget.identity),
            part=str(widget.part.identity),
            standing=str(widget.standing),
        )


class MapToSaveWidgetRequest(ts.Mapper, ports.SaveWidgetRequest):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(
            name=str(widget.identity),
            part=str(widget.part.identity),
            standing=str(widget.standing),
        )


class MapToLoadWidgetRequest(ts.Mapper, ports.LoadWidgetRequest):

    def __init__(self, name: domain.Name) -> None:
        super().__init__(name=str(name))


class MapToFindWidgetRequest(ts.Mapper, ports.FindWidgetRequest):

    def __init__(self, name: domain.Name) -> None:
        super().__init__(name=str(name))


class MapToAddPartResponse(ts.Mapper, client.AddPartResponse):

    def __init__(
        self, add_widget_response: ports.AddWidgetResponse, widget: domain.Widget
    ) -> None:
        match add_widget_response.outcome:
            case ports.AddWidgetOutcome.ADDED:
                pass
            case ports.AddWidgetOutcome.EXISTS:
                raise client.WidgetExists(
                    message=f"widget {add_widget_response.name!r} is already stored"
                )
            case _ as never:
                typing.assert_never(never)
        super().__init__(
            name=str(widget.identity),
            part=str(widget.part.identity),
            standing=str(widget.standing),
        )


class MapToTakePartResponse(ts.Mapper, client.TakePartResponse):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(
            name=str(widget.identity),
            part=str(widget.part.identity),
            standing=str(widget.standing),
        )


class AlphaService(ts.ApplicationService):

    def __init__(self, widget_store: ports.WidgetStore, beta_check: ports.BetaCheck) -> None:
        self._widget_store = widget_store
        self._beta_check = beta_check

    async def add_part(self, add_part_request: client.AddPartRequest) -> client.AddPartResponse:
        try:
            widget = domain.Widget(MapToWidgetSpec(add_part_request))
            taken = widget.take(MapToPartSpec(add_part_request))
        except errors.DomainError as domain_error:
            raise client.WidgetRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        match taken:
            case domain.Taken.TAKEN:
                pass
            case domain.Taken.HELD:
                check_name_response = await self._beta_check.check_name(
                    MapToCheckNameRequest(widget)
                )
                widget.clear(MapToClearanceSpec(check_name_response))
            case _ as never:
                typing.assert_never(never)
        async with self._widget_store.transaction() as widget_repository:
            add_widget_response = await widget_repository.add_widget(
                MapToAddWidgetRequest(widget)
            )
        return MapToAddPartResponse(add_widget_response, widget)

    async def take_part(
        self, take_part_request: client.TakePartRequest
    ) -> client.TakePartResponse:
        try:
            name = domain.Name(take_part_request.name)
        except errors.DomainError as domain_error:
            raise client.WidgetRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        async with self._widget_store.transaction() as widget_repository:
            load_widget_request = MapToLoadWidgetRequest(name)
            load_widget_response = await widget_repository.load_widget(load_widget_request)
            widget = domain.Widget(
                MapToLoadedWidgetSpec(load_widget_request, load_widget_response)
            )
            taken = widget.take(MapToTakenPartSpec(take_part_request))
            match taken:
                case domain.Taken.TAKEN:
                    await widget_repository.save_widget(MapToSaveWidgetRequest(widget))
                case domain.Taken.HELD:
                    pass
                case _ as never:
                    typing.assert_never(never)
        return MapToTakePartResponse(widget)

    async def find_widget(
        self, find_widget_request: client.FindWidgetRequest
    ) -> client.FindWidgetResponse:
        try:
            name = domain.Name(find_widget_request.name)
        except errors.DomainError as domain_error:
            raise client.WidgetRejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        async with self._widget_store.transaction() as widget_repository:
            find_widget_response = await widget_repository.find_widget(
                MapToFindWidgetRequest(name)
            )
        return client.FindWidgetResponse(found=find_widget_response.outcome.value)
