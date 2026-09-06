from __future__ import annotations

import pytest
import tesser.testing as ts

import protocol
import tessercheck.adapters.handlers as handlers
import tessercheck.client as client


@ts.fake
class FakeCheckClient(client.TessercheckClient):
    def __init__(self, *findings: str) -> None:
        self.findings = findings
        self.roots: list[str] = []

    def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        self.roots.append(check_request.tree)
        return client.CheckResponse(findings=self.findings)

    def rulebook(self, rulebook_request: client.RulebookRequest) -> client.RulebookResponse:
        self.roots.append(rulebook_request.tree)
        return client.RulebookResponse(rendered="| rendered |")


def test_the_tree_argument_reaches_the_client() -> None:
    fake_check_client = FakeCheckClient()
    cli_response = handlers.Handler(fake_check_client).check(protocol.CliRequest(("some/tree",)))
    assert fake_check_client.roots == ["some/tree"]
    assert cli_response.exit_code == 0


def test_no_argument_checks_the_working_directory() -> None:
    fake_check_client = FakeCheckClient()
    handlers.Handler(fake_check_client).check(protocol.CliRequest(()))
    assert fake_check_client.roots == ["."]


def test_findings_become_lines_and_a_failing_exit_code() -> None:
    fake_check_client = FakeCheckClient("a.py:1: TB040 one", "b.py:2: TB041 two")
    cli_response = handlers.Handler(fake_check_client).check(protocol.CliRequest(("tree",)))
    assert cli_response.exit_code == 1
    assert cli_response.stdout == "a.py:1: TB040 one\nb.py:2: TB041 two"
    assert cli_response.stderr == ""


def test_a_clean_tree_prints_nothing_and_exits_zero() -> None:
    cli_response = handlers.Handler(FakeCheckClient()).check(protocol.CliRequest(("tree",)))
    assert cli_response.exit_code == 0
    assert cli_response.stdout == ""


def test_an_extra_argument_is_a_usage_error() -> None:
    fake_check_client = FakeCheckClient()
    with pytest.raises(protocol.UsageError):
        handlers.Handler(fake_check_client).check(protocol.CliRequest(("tree", "surplus")))
    assert fake_check_client.roots == []
