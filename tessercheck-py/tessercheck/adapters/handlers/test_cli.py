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

    def mark(self, mark_request: client.MarkRequest) -> client.MarkResponse:
        self.roots.append(mark_request.tree)
        return client.MarkResponse(files=0, remaining=self.findings)

    def rename(self, rename_request: client.RenameRequest) -> client.RenameResponse:
        self.roots.append(rename_request.tree)
        return client.RenameResponse(files=0, remaining=self.findings)

    def rulebook(self, rulebook_request: client.RulebookRequest) -> client.RulebookResponse:
        self.roots.append(rulebook_request.tree)
        return client.RulebookResponse(rendered="| rendered |")


@ts.fake
class FakeRejectingClient(client.TessercheckClient):

    def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        raise client.Rejected("unreadable", "checks.py cannot be read")

    def mark(self, mark_request: client.MarkRequest) -> client.MarkResponse:
        raise client.Rejected("unreadable", "checks.py cannot be read")

    def rename(self, rename_request: client.RenameRequest) -> client.RenameResponse:
        raise client.Rejected("unreadable", "checks.py cannot be read")

    def rulebook(self, rulebook_request: client.RulebookRequest) -> client.RulebookResponse:
        raise client.Rejected("unreadable", "checks.py cannot be read")


def test_a_rejected_check_exits_two_with_the_context_s_message() -> None:
    cli_response = handlers.Handler(FakeRejectingClient()).check(protocol.CliRequest(("tree",)))
    assert cli_response == protocol.CliResponse(2, stdout="", stderr="checks.py cannot be read")


def test_a_rejected_mark_exits_two_with_the_context_s_message() -> None:
    cli_response = handlers.Handler(FakeRejectingClient()).mark(protocol.CliRequest(("tree",)))
    assert cli_response == protocol.CliResponse(2, stdout="", stderr="checks.py cannot be read")


def test_a_rejected_rename_exits_two_with_the_context_s_message() -> None:
    cli_response = handlers.Handler(FakeRejectingClient()).rename(protocol.CliRequest(("tree",)))
    assert cli_response == protocol.CliResponse(2, stdout="", stderr="checks.py cannot be read")


def test_a_rejected_rulebook_exits_two_with_the_context_s_message() -> None:
    cli_response = handlers.Handler(FakeRejectingClient()).rulebook(protocol.CliRequest(("tree",)))
    assert cli_response == protocol.CliResponse(2, stdout="", stderr="checks.py cannot be read")


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


def test_the_tree_argument_reaches_the_client_on_a_mark() -> None:
    fake_check_client = FakeCheckClient()
    cli_response = handlers.Handler(fake_check_client).mark(protocol.CliRequest(("some/tree",)))
    assert fake_check_client.roots == ["some/tree"]
    assert cli_response.exit_code == 0
    assert cli_response.stdout == "marked 0 file(s)"
    assert cli_response.stderr == ""


def test_no_argument_marks_the_working_directory() -> None:
    fake_check_client = FakeCheckClient()
    handlers.Handler(fake_check_client).mark(protocol.CliRequest(()))
    assert fake_check_client.roots == ["."]


def test_what_a_mark_cannot_write_becomes_lines_and_a_failing_exit_code() -> None:
    fake_check_client = FakeCheckClient("a.py:1: TB044 one", "b.py:2: TB045 two")
    cli_response = handlers.Handler(fake_check_client).mark(protocol.CliRequest(("tree",)))
    assert cli_response.exit_code == 1
    assert cli_response.stdout == (
        "marked 0 file(s)\n"
        "2 finding(s) this cannot mark:\n"
        "a.py:1: TB044 one\n"
        "b.py:2: TB045 two"
    )
    assert cli_response.stderr == ""


def test_an_extra_argument_to_mark_is_a_usage_error() -> None:
    fake_check_client = FakeCheckClient()
    with pytest.raises(protocol.UsageError):
        handlers.Handler(fake_check_client).mark(protocol.CliRequest(("tree", "surplus")))
