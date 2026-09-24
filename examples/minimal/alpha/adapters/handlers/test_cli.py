from __future__ import annotations

import tesser.testing as ts

import alpha.adapters.handlers as handlers
import alpha.client as client
import protocol


@ts.fake
class FakeClient(client.AlphaClient):

    async def add_part(self, add_part_request: client.AddPartRequest) -> client.AddPartResponse:
        return client.AddPartResponse(name=add_part_request.name, standing="kept")

    async def create_widget(self, create_widget_request: client.CreateWidgetRequest) -> client.CreateWidgetResponse:
        return client.CreateWidgetResponse(name=create_widget_request.name)

    async def approve_widget(self, approve_widget_request: client.ApproveWidgetRequest) -> client.ApproveWidgetResponse:
        return client.ApproveWidgetResponse(name=approve_widget_request.name)

    async def find_widget(self, find_widget_request: client.FindWidgetRequest) -> client.FindWidgetResponse:
        return client.FindWidgetResponse(found="yes")


@ts.fake
class FakeRejectingClient(client.AlphaClient):

    async def add_part(self, add_part_request: client.AddPartRequest) -> client.AddPartResponse:
        raise client.WidgetRejected("empty_name", "a name is never empty")

    async def create_widget(self, create_widget_request: client.CreateWidgetRequest) -> client.CreateWidgetResponse:
        raise client.WidgetRejected("empty_name", "a name is never empty")

    async def approve_widget(self, approve_widget_request: client.ApproveWidgetRequest) -> client.ApproveWidgetResponse:
        raise client.WidgetRejected("empty_name", "a name is never empty")

    async def find_widget(self, find_widget_request: client.FindWidgetRequest) -> client.FindWidgetResponse:
        raise client.WidgetRejected("empty_name", "a name is never empty")


class TestHandler:

    async def test_each_command_prints_the_widget_s_name_or_found(self) -> None:
        handler = handlers.Handler(FakeClient())
        printed = [
            (await handler.add_part(protocol.CliRequest(args=("a", "p")))).line.text,
            (await handler.create_widget(protocol.CliRequest(args=("a",)))).line.text,
            (await handler.approve_widget(protocol.CliRequest(args=("a",)))).line.text,
            (await handler.find_widget(protocol.CliRequest(args=("a",)))).line.text,
        ]
        assert printed == ["a", "a", "a", "yes"]

    async def test_a_rejection_exits_two_with_the_context_s_message(self) -> None:
        handler = handlers.Handler(FakeRejectingClient())
        cli_response = await handler.add_part(protocol.CliRequest(args=("a", "p")))
        assert cli_response == protocol.CliResponse(exit_code=2, line=protocol.Line(text="a name is never empty"))
