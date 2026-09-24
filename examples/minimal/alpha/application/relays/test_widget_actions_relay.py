from __future__ import annotations

import alpha.application.relays as relays


class TestKeepWidgetSnapshots:

    def test_each_message_is_its_name_and_comes_back_equal(self) -> None:
        keep_widget_request = relays.KeepWidgetRequest(name="a")
        keep_widget_response = relays.KeepWidgetResponse(name="a")
        request_bytes = relays.KeepWidgetRequestSnapshot().serialize(keep_widget_request)
        response_bytes = relays.KeepWidgetResponseSnapshot().serialize(keep_widget_response)
        assert request_bytes == response_bytes == b'{"name": "a"}'
        assert relays.KeepWidgetRequestSnapshot().deserialize(request_bytes) == keep_widget_request
        assert relays.KeepWidgetResponseSnapshot().deserialize(response_bytes) == keep_widget_response
