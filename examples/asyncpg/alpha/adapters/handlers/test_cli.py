from __future__ import annotations

import pytest

import tesser.testing as ts

import alpha.adapters.handlers as handlers
import alpha.client as client
import protocol


@ts.fake
class FakeClient(client.AlphaClient):

    async def add(self, add_request: client.AddRequest) -> client.AddResponse:
        return client.AddResponse(name=add_request.name, part=add_request.part, standing="kept")

    async def take(self, take_request: client.TakeRequest) -> client.TakeResponse:
        return client.TakeResponse(name=take_request.name, part=take_request.part, standing="kept")

    async def find(self, find_request: client.FindRequest) -> client.FindResponse:
        return client.FindResponse(found="no")


@ts.fake
class FakeRefusingClient(client.AlphaClient):

    def __init__(self, error: Exception) -> None:
        self.error = error

    async def add(self, add_request: client.AddRequest) -> client.AddResponse:
        raise self.error

    async def take(self, take_request: client.TakeRequest) -> client.TakeResponse:
        raise self.error

    async def find(self, find_request: client.FindRequest) -> client.FindResponse:
        raise self.error


class TestHandler:

    async def test_add_prints_the_name_the_part_and_the_standing(self) -> None:
        handler = handlers.Handler(FakeClient())
        cli_response = await handler.add(protocol.CliRequest(args=("a", "p")))
        assert cli_response.line == protocol.Line(text="a p kept")

    async def test_a_rejection_exits_two_and_prints_the_contexts_wording(self) -> None:
        handler = handlers.Handler(
            FakeRefusingClient(client.Rejected("empty_name", "a name is never empty"))
        )
        cli_response = await handler.add(protocol.CliRequest(args=("a", "p")))
        assert cli_response.exit_code == 2
        assert cli_response.line == protocol.Line(text="a name is never empty")

    async def test_a_missing_widget_exits_one_and_prints_the_contexts_wording(self) -> None:
        handler = handlers.Handler(
            FakeRefusingClient(client.Missing("unknown_widget", "no widget 'a'"))
        )
        cli_response = await handler.add(protocol.CliRequest(args=("a", "p")))
        assert cli_response.exit_code == 1
        assert cli_response.line == protocol.Line(text="no widget 'a'")

    async def test_a_conflict_exits_one_and_prints_the_contexts_wording(self) -> None:
        handler = handlers.Handler(
            FakeRefusingClient(client.Conflict("widget_exists", "widget 'a' is already stored"))
        )
        cli_response = await handler.add(protocol.CliRequest(args=("a", "p")))
        assert cli_response.exit_code == 1
        assert cli_response.line == protocol.Line(text="widget 'a' is already stored")

    async def test_an_unavailable_dependency_exits_one_and_prints_the_contexts_wording(self) -> None:
        handler = handlers.Handler(
            FakeRefusingClient(client.Unavailable("the widget store is unavailable"))
        )
        cli_response = await handler.add(protocol.CliRequest(args=("a", "p")))
        assert cli_response.exit_code == 1
        assert cli_response.line == protocol.Line(text="the widget store is unavailable")

    async def test_a_failure_the_context_never_declared_leaves_the_handler(self) -> None:
        handler = handlers.Handler(
            FakeRefusingClient(RuntimeError("a stack trace nobody should see"))
        )
        with pytest.raises(RuntimeError):
            await handler.add(protocol.CliRequest(args=("a", "p")))
