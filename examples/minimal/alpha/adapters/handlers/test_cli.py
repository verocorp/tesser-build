from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers as handlers
import alpha.client as client
import protocol


@ts.fake
class FakeClient(client.AlphaClient):

    def add_part(self, add_part_request: client.AddPartRequest) -> client.AddPartResponse:
        return client.AddPartResponse(name=add_part_request.name, standing="kept")

    def create_widget(self, create_widget_request: client.CreateWidgetRequest) -> client.CreateWidgetResponse:
        return client.CreateWidgetResponse(name=create_widget_request.name)


@ts.fake
class FakeRejectingClient(client.AlphaClient):

    def add_part(self, add_part_request: client.AddPartRequest) -> client.AddPartResponse:
        raise client.WidgetRejected("empty_name", "a name is never empty")

    def create_widget(self, create_widget_request: client.CreateWidgetRequest) -> client.CreateWidgetResponse:
        raise client.WidgetRejected("empty_name", "a name is never empty")


class TestHandler:

    def test_add_prints_the_added_name(self) -> None:
        handler = handlers.Handler(FakeClient())
        cli_response = handler.add_part(protocol.CliRequest(args=("a", "p")))
        assert cli_response.line == protocol.Line(text="a")

    def test_a_rejection_exits_two_with_the_context_s_message(self) -> None:
        handler = handlers.Handler(FakeRejectingClient())
        cli_response = handler.add_part(protocol.CliRequest(args=("a", "p")))
        assert cli_response == protocol.CliResponse(exit_code=2, line=protocol.Line(text="a name is never empty"))
