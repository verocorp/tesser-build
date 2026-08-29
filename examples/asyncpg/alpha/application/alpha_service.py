from __future__ import annotations

import typing

import tesser.application as ts

import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.widget_repository as widget_repository
import alpha.client.client as client
import alpha.domain.widget as widget


class MapToWidgetSpec(ts.Mapper, widget.WidgetSpec):

    def __init__(self, request: client.AddRequest) -> None:
        super().__init__(name=request.name, part=widget.PartSpec(id=request.name))


class MapToLoadedWidgetSpec(ts.Mapper, widget.WidgetSpec):

    def __init__(self, loaded: widget_repository.LoadWidgetResponse) -> None:
        super().__init__(name=loaded.name, part=widget.PartSpec(id=loaded.part))


class MapToPartSpec(ts.Mapper, widget.PartSpec):

    def __init__(self, request: client.AddRequest) -> None:
        super().__init__(id=request.part)


class MapToTakenPartSpec(ts.Mapper, widget.PartSpec):

    def __init__(self, request: client.TakeRequest) -> None:
        super().__init__(id=request.part)


class MapToCheckRequest(ts.Mapper, beta_check.CheckRequest):

    def __init__(self, added: widget.Widget) -> None:
        super().__init__(name=str(added.identity))


class MapToSaveWidgetRequest(ts.Mapper, widget_repository.SaveWidgetRequest):

    def __init__(self, saved: widget.Widget) -> None:
        super().__init__(name=str(saved.identity), part=str(saved.part.identity))


class MapToLoadWidgetRequest(ts.Mapper, widget_repository.LoadWidgetRequest):

    def __init__(self, sought: widget.Name) -> None:
        super().__init__(name=str(sought))


class MapToFindWidgetRequest(ts.Mapper, widget_repository.FindWidgetRequest):

    def __init__(self, sought: widget.Name) -> None:
        super().__init__(name=str(sought))


class MapToAddResponse(ts.Mapper, client.AddResponse):

    def __init__(self, added: widget.Widget) -> None:
        super().__init__(name=str(added.identity))


class MapToTakeResponse(ts.Mapper, client.TakeResponse):

    def __init__(self, taken_widget: widget.Widget) -> None:
        super().__init__(name=str(taken_widget.identity), part=str(taken_widget.part.identity))


class AlphaService(ts.ApplicationService):

    def __init__(self, widget_store: widget_repository.WidgetStore, checks: beta_check.BetaCheck) -> None:
        self._widget_store = widget_store
        self._checks = checks

    async def add(self, request: client.AddRequest) -> client.AddResponse:
        added = widget.Widget(MapToWidgetSpec(request))
        taken = added.take(MapToPartSpec(request))
        match taken:
            case widget.Taken.TAKEN:
                async with self._widget_store.transaction() as widgets_repo:
                    await widgets_repo.save_widget(MapToSaveWidgetRequest(added))
            case widget.Taken.HELD:
                await self._checks.check(MapToCheckRequest(added))
            case _ as never:
                typing.assert_never(never)
        return MapToAddResponse(added)

    async def take(self, request: client.TakeRequest) -> client.TakeResponse:
        sought = widget.Name(request.name)
        async with self._widget_store.transaction() as widgets_repo:
            loaded = await widgets_repo.load_widget(MapToLoadWidgetRequest(sought))
            taking_widget = widget.Widget(MapToLoadedWidgetSpec(loaded))
            taken = taking_widget.take(MapToTakenPartSpec(request))
            match taken:
                case widget.Taken.TAKEN:
                    await widgets_repo.save_widget(MapToSaveWidgetRequest(taking_widget))
                case widget.Taken.HELD:
                    pass
                case _ as never:
                    typing.assert_never(never)
        return MapToTakeResponse(taking_widget)

    async def find(self, request: client.FindRequest) -> client.FindResponse:
        sought = widget.Name(request.name)
        async with self._widget_store.transaction() as widgets_repo:
            answer = await widgets_repo.find_widget(MapToFindWidgetRequest(sought))
        return client.FindResponse(found=answer.found.value)
