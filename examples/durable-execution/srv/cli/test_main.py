from __future__ import annotations

import os

import srv.cli.main as main


class TestCliHost:

    def test_a_usage_error_exits_two(self) -> None:
        os.environ.update(RESTATE_INGRESS="http://localhost:8080")
        exit_code = main.CliHost().run(["o1", "widget"])
        assert exit_code == 2

    def test_an_invalid_order_exits_by_its_kind(self) -> None:
        os.environ.update(RESTATE_INGRESS="http://localhost:8080")
        exit_code = main.CliHost().run(["o1", "widget", "0"])
        assert exit_code == 2
