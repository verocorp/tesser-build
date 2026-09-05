from __future__ import annotations

import pytest

import protocol.cli as cli


class TestCliRequest:

    def test_a_missing_argument_is_a_usage_error(self) -> None:
        cli_request = cli.CliRequest(args=())
        with pytest.raises(cli.UsageError):
            cli_request.arg(0, "name", "usage: add <name>")
