from __future__ import annotations

import tesser.application as ts

import alpha.application.ports as ports
import alpha.application.relays as relays
import alpha.domain as domain


class MapToSaveWidgetRequest(ts.Mapper, ports.SaveWidgetRequest):

    def __init__(self, name: domain.Name, standing: domain.Standing) -> None:
        super().__init__(name=str(name), standing=str(standing))


class MapToKeepWidgetResponse(ts.Mapper, relays.KeepWidgetResponse):

    def __init__(self, save_widget_response: ports.SaveWidgetResponse) -> None:
        super().__init__(name=save_widget_response.name)


class WidgetActions(ts.Actions):

    def __init__(self, widget_store: ports.WidgetStore) -> None:
        self._widget_store = widget_store

    async def keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        name = domain.Name(keep_widget_request.name)
        standing = domain.Standing("kept")
        async with self._widget_store.transaction() as widget_repository:
            save_widget_response = await widget_repository.save_widget(MapToSaveWidgetRequest(name, standing))
        return MapToKeepWidgetResponse(save_widget_response)
