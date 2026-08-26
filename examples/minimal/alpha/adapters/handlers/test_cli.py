from __future__ import annotations

import pytest
import tesser.testing as ts

import alpha.adapters.handlers.cli as cli
import alpha.client.client as client
import protocol.cli as protocol_cli
import tesser.errors as errors


@ts.fake
class FakeClient(client.Client):

    def add(self, request: client.AddRequest) -> client.AddResponse:
        view = client.WholeView(id=request.id, name=request.name, count=request.count)
        return client.AddResponse(wholes=(view,))

    def get(self, request: client.GetRequest) -> client.GetResponse:
        raise errors.not_found("missing_whole", "no such whole")


def test_add_reports_the_added_id() -> None:
    handler = cli.Handler(FakeClient())
    response = handler.add(protocol_cli.CliRequest(args=("w", "a", "1")))
    assert response.line == protocol_cli.Line(text="w")


def test_add_rejects_a_bad_count() -> None:
    handler = cli.Handler(FakeClient())
    with pytest.raises(protocol_cli.UsageError):
        handler.add(protocol_cli.CliRequest(args=("w", "a", "x")))


def test_get_maps_a_domain_error_to_an_exit_code() -> None:
    handler = cli.Handler(FakeClient())
    response = handler.get(protocol_cli.CliRequest(args=("w",)))
    assert response.exit_code == 1
