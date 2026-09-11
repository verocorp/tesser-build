from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.ports as ports
import alpha.client as client
import alpha.domain as domain
import tesser.errors as errors


class MapToWidgetSpec(ts.Mapper, domain.WidgetSpec):

    def __init__(self, add_request: client.AddRequest) -> None:
        super().__init__(
            name=add_request.name, part=domain.PartSpec(id=add_request.name), standing="kept"
        )


class MapToLoadedWidgetSpec(ts.Mapper, domain.WidgetSpec):

    def __init__(
        self,
        load_widget_request: ports.LoadWidgetRequest,
        load_widget_response: ports.LoadWidgetResponse,
    ) -> None:
        match load_widget_response.outcome:
            case ports.Loaded.FOUND:
                record = load_widget_response.widgets[0]
            case ports.Loaded.MISSING:
                raise client.Missing(
                    code="unknown_widget",
                    message=f"no widget {load_widget_request.name!r}",
                )
            case _ as never:
                typing.assert_never(never)
        super().__init__(
            name=record.name,
            part=domain.PartSpec(id=record.part),
            standing=record.standing,
        )


class MapToPartSpec(ts.Mapper, domain.PartSpec):

    def __init__(self, add_request: client.AddRequest) -> None:
        super().__init__(id=add_request.part)


class MapToTakenPartSpec(ts.Mapper, domain.PartSpec):

    def __init__(self, take_request: client.TakeRequest) -> None:
        super().__init__(id=take_request.part)


class MapToCheckRequest(ts.Mapper, ports.CheckRequest):

    def __init__(self, widget: domain.Widget) -> None:
        super().__init__(name=str(widget.identity))


class MapToClearanceSpec(ts.Mapper, domain.ClearanceSpec):

    def __init__(self, check_response: ports.CheckResponse) -> None:
        super().__init__(verdict=check_response.verdict.value)


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


class MapToAddResponse(ts.Mapper, client.AddResponse):

    def __init__(
        self, add_widget_response: ports.AddWidgetResponse, widget: domain.Widget
    ) -> None:
        match add_widget_response.outcome:
            case ports.Added.ADDED:
                pass
            case ports.Added.EXISTS:
                raise client.Conflict(
                    code="widget_exists",
                    message=f"widget {add_widget_response.name!r} is already stored",
                )
            case _ as never:
                typing.assert_never(never)
        super().__init__(
            name=str(widget.identity),
            part=str(widget.part.identity),
            standing=str(widget.standing),
        )


class MapToTakeResponse(ts.Mapper, client.TakeResponse):

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

    async def add(self, add_request: client.AddRequest) -> client.AddResponse:
        try:
            widget = domain.Widget(MapToWidgetSpec(add_request))
            taken = widget.take(MapToPartSpec(add_request))
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        match taken:
            case domain.Taken.TAKEN:
                pass
            case domain.Taken.HELD:
                check_response = await self._beta_check.check(MapToCheckRequest(widget))
                widget.clear(MapToClearanceSpec(check_response))
            case _ as never:
                typing.assert_never(never)
        async with self._widget_store.transaction() as widget_repository:
            add_widget_response = await widget_repository.add_widget(
                MapToAddWidgetRequest(widget)
            )
        return MapToAddResponse(add_widget_response, widget)

    async def take(self, take_request: client.TakeRequest) -> client.TakeResponse:
        try:
            name = domain.Name(take_request.name)
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        async with self._widget_store.transaction() as widget_repository:
            load_widget_request = MapToLoadWidgetRequest(name)
            load_widget_response = await widget_repository.load_widget(load_widget_request)
            widget = domain.Widget(
                MapToLoadedWidgetSpec(load_widget_request, load_widget_response)
            )
            taken = widget.take(MapToTakenPartSpec(take_request))
            match taken:
                case domain.Taken.TAKEN:
                    await widget_repository.save_widget(MapToSaveWidgetRequest(widget))
                case domain.Taken.HELD:
                    pass
                case _ as never:
                    typing.assert_never(never)
        return MapToTakeResponse(widget)

    async def find(self, find_request: client.FindRequest) -> client.FindResponse:
        try:
            name = domain.Name(find_request.name)
        except errors.DomainError as domain_error:
            raise client.Rejected(
                code=domain_error.code, message=domain_error.message
            ) from domain_error
        async with self._widget_store.transaction() as widget_repository:
            find_widget_response = await widget_repository.find_widget(
                MapToFindWidgetRequest(name)
            )
        return client.FindResponse(found=find_widget_response.found.value)
