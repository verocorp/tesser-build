from __future__ import annotations

import pytest

import protocol


class TestCliRequest:

    def test_a_missing_argument_is_a_usage_error(self) -> None:
        cli_request = protocol.CliRequest(args=())
        with pytest.raises(protocol.UsageError):
            cli_request.arg(0, "name", "usage: add <name>")
