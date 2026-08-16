from __future__ import annotations

import pytest
import tesser.testing as ts

import tessercheck.adapters.handlers.cli as cli
import tessercheck.client.client as client
from protocol.cli import CliRequest, UsageError


@ts.fake
class FakeCheckClient(client.Client):
    def __init__(self, *findings: str) -> None:
        self.findings = findings
        self.roots: list[str] = []

    def check(self, request: client.CheckRequest) -> client.CheckResponse:
        self.roots.append(request.root)
        return client.CheckResponse(findings=self.findings)

    def rulebook(self, request: client.RulebookRequest) -> client.RulebookResponse:
        self.roots.append(request.root)
        return client.RulebookResponse(rendered="| rendered |")


def test_the_tree_argument_reaches_the_client() -> None:
    fake = FakeCheckClient()
    resp = cli.Handler(fake).check(CliRequest(("some/tree",)))
    assert fake.roots == ["some/tree"]
    assert resp.exit_code == 0


def test_no_argument_checks_the_working_directory() -> None:
    fake = FakeCheckClient()
    cli.Handler(fake).check(CliRequest(()))
    assert fake.roots == ["."]


def test_findings_become_lines_and_a_failing_exit_code() -> None:
    fake = FakeCheckClient("a.py:1: TB040 one", "b.py:2: TB041 two")
    resp = cli.Handler(fake).check(CliRequest(("tree",)))
    assert resp.exit_code == 1
    assert resp.stdout == "a.py:1: TB040 one\nb.py:2: TB041 two"
    assert resp.stderr == ""


def test_a_clean_tree_prints_nothing_and_exits_zero() -> None:
    resp = cli.Handler(FakeCheckClient()).check(CliRequest(("tree",)))
    assert resp.exit_code == 0
    assert resp.stdout == ""


def test_an_extra_argument_is_a_usage_error() -> None:
    fake = FakeCheckClient()
    with pytest.raises(UsageError):
        cli.Handler(fake).check(CliRequest(("tree", "surplus")))
    assert fake.roots == []
