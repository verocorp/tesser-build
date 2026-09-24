from __future__ import annotations

import alpha.application.relays as relays


class TestAwaitApproveWidgetResponseSnapshot:

    def test_the_promise_named_for_its_operation_carries_the_name_it_approved(self) -> None:
        await_approve_widget_response = relays.AwaitApproveWidgetResponse(name="a")
        await_approve_widget_response_snapshot = relays.AwaitApproveWidgetResponseSnapshot()
        assert relays.APPROVE_WIDGET_PROMISE == "approve_widget"
        assert await_approve_widget_response_snapshot.deserialize(
            await_approve_widget_response_snapshot.serialize(await_approve_widget_response)
        ) == await_approve_widget_response
