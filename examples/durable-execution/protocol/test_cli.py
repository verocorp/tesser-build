from __future__ import annotations

import pytest

import protocol.cli as cli


class TestCliRequest:

    def test_a_missing_argument_is_a_usage_error(self) -> None:
        request = cli.CliRequest(args=())
        with pytest.raises(cli.UsageError):
            request.arg(0, "order_id", "usage: place <order_id>")

    def test_an_integer_argument_is_parsed(self) -> None:
        request = cli.CliRequest(args=("3",))
        assert request.integer(0, "quantity", "usage") == 3

    def test_a_non_integer_argument_is_a_usage_error(self) -> None:
        request = cli.CliRequest(args=("three",))
        with pytest.raises(cli.UsageError):
            request.integer(0, "quantity", "usage")
