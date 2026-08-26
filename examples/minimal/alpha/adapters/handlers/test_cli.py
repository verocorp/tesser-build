from __future__ import annotations

import pytest
import tesser.testing as ts

import alpha.adapters.handlers.cli as cli
import alpha.client.client as client
import protocol.cli as protocol_cli


@ts.fake
class FakeClient(client.Client):

    def add(self, request: client.AddRequest) -> client.AddResponse:
        return client.AddResponse(name=request.name)


def test_add_prints_the_added_name() -> None:
    response = cli.Handler(FakeClient()).add(protocol_cli.CliRequest(args=("a",)))
    assert response.line == protocol_cli.Line(text="a")


def test_add_without_a_name_is_a_usage_error() -> None:
    with pytest.raises(protocol_cli.UsageError):
        cli.Handler(FakeClient()).add(protocol_cli.CliRequest(args=()))
