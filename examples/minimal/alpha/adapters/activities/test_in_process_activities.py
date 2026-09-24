from __future__ import annotations

import tesser.testing as ts
import in_process

import alpha.adapters.activities as activities
import alpha.application.client as client
import alpha.application.relays as relays


@ts.fake
class FakeWidgetApplicationClient(client.WidgetApplicationClient):

    def __init__(self) -> None:
        self.kept: list[str] = []

    def keep_widget(self, keep_widget_request: relays.KeepWidgetRequest) -> relays.KeepWidgetResponse:
        self.kept.append(keep_widget_request.name)
        return relays.KeepWidgetResponse(name=keep_widget_request.name)


class TestInProcessKeepWidget:

    def test_the_engine_holds_keep_widget_under_its_operation(self) -> None:
        widget_actions_service = in_process.Service("WidgetActions")
        in_process_keep_widget = activities.InProcessKeepWidget(widget_actions_service, FakeWidgetApplicationClient())
        assert widget_actions_service.handlers == {"keep_widget": in_process_keep_widget.handler}

    def test_a_call_made_with_its_handler_reaches_the_application_client(self) -> None:
        fake_widget_application_client = FakeWidgetApplicationClient()
        in_process_keep_widget = activities.InProcessKeepWidget(
            in_process.Service("WidgetActions"), fake_widget_application_client
        )
        keep_widget_response = in_process.service_call(in_process_keep_widget.handler, relays.KeepWidgetRequest(name="a"))
        assert keep_widget_response.name == "a"
        assert fake_widget_application_client.kept == ["a"]
