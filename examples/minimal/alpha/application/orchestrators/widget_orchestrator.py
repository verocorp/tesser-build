from __future__ import annotations

import tesser.application as ts

import alpha.application.relays as relays
import alpha.domain as domain


class MapToAwaitApproveWidgetRequest(ts.Mapper, relays.AwaitApproveWidgetRequest):

    def __init__(self, name: domain.Name) -> None:
        super().__init__(name=str(name))


class MapToKeepWidgetRequest(ts.Mapper, relays.KeepWidgetRequest):

    def __init__(self, name: domain.Name) -> None:
        super().__init__(name=str(name))


class MapToRegisterWidgetResponse(ts.Mapper, relays.RegisterWidgetResponse):

    def __init__(self, keep_widget_response: relays.KeepWidgetResponse) -> None:
        super().__init__(name=keep_widget_response.name)


class WidgetOrchestrator(ts.Orchestrator):

    def __init__(
        self,
        widget_orchestrator_signal_relay: relays.WidgetOrchestratorSignalRelay,
        widget_actions_relay: relays.WidgetActionsRelay,
    ) -> None:
        self._widget_orchestrator_signal_relay = widget_orchestrator_signal_relay
        self._widget_actions_relay = widget_actions_relay

    def register_widget(self, register_widget_request: relays.RegisterWidgetRequest) -> relays.RegisterWidgetResponse:
        name = domain.Name(register_widget_request.name)
        self._widget_orchestrator_signal_relay.await_approve_widget(MapToAwaitApproveWidgetRequest(name))
        keep_widget_response = self._widget_actions_relay.run_keep_widget(MapToKeepWidgetRequest(name))
        return MapToRegisterWidgetResponse(keep_widget_response)
