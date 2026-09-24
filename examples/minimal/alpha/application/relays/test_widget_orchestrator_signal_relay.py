from __future__ import annotations

import alpha.application.relays as relays


class TestApproveWidgetPromise:

    def test_the_promise_is_named_for_the_operation_that_resolves_it(self) -> None:
        assert relays.APPROVE_WIDGET_PROMISE == "approve_widget"
