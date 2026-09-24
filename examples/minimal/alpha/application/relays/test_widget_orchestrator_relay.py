from __future__ import annotations

import alpha.application.relays as relays
import alpha.domain as domain


class TestWidgetOrchestratorSnapshots:

    def test_each_message_is_its_name_and_comes_back_equal(self) -> None:
        register_widget_request = relays.RegisterWidgetRequest(name=domain.Name("a"))
        register_widget_response = relays.RegisterWidgetResponse(name="a")
        approve_widget_request = relays.ApproveWidgetRequest(name="a")
        approve_widget_response = relays.ApproveWidgetResponse(name="a")
        assert relays.RegisterWidgetRequestSnapshot().deserialize(
            relays.RegisterWidgetRequestSnapshot().serialize(register_widget_request)
        ) == register_widget_request
        assert relays.RegisterWidgetResponseSnapshot().deserialize(
            relays.RegisterWidgetResponseSnapshot().serialize(register_widget_response)
        ) == register_widget_response
        assert relays.ApproveWidgetRequestSnapshot().deserialize(
            relays.ApproveWidgetRequestSnapshot().serialize(approve_widget_request)
        ) == approve_widget_request
        assert relays.ApproveWidgetResponseSnapshot().deserialize(
            relays.ApproveWidgetResponseSnapshot().serialize(approve_widget_response)
        ) == approve_widget_response
