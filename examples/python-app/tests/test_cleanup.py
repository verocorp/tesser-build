"""Partial-construction cleanup. The CleanupStack closes in reverse and keeps going
even when a close itself raises (covering the hard cases, not just a happy-path
counter); and ``bootstrap.new`` closes what it already built when a later dep fails.
"""

from __future__ import annotations

import pytest

import linkpolicy.wiring.wire as linkpolicy_wire
from bootstrap.bootstrap import CleanupStack, new
from bootstrap.config import Config
from campaign.wiring.config import Config as CampaignConfig
from errors import DomainError
from lifecycle import Closeable
from linkpolicy import CheckRequest, CheckResponse, Client, VerdictView
from linkpolicy.wiring.config import Config as LinkPolicyConfig


class _Spy:
    def __init__(self, name: str, order: list[str], *, fail: bool = False) -> None:
        self.name = name
        self._order = order
        self._fail = fail
        self.closed = False

    def close(self) -> None:
        self.closed = True
        self._order.append(self.name)
        if self._fail:
            raise RuntimeError(f"{self.name} close failed")


def test_stack_closes_reverse_order_and_all_despite_error() -> None:
    order: list[str] = []
    a, b, c = _Spy("a", order), _Spy("b", order, fail=True), _Spy("c", order)
    stack = CleanupStack()
    for r in (a, b, c):
        stack.push(r)
    errors = stack.close_all()
    assert order == ["c", "b", "a"]  # reverse of construction
    assert a.closed and b.closed and c.closed  # a leaky close (b) does not orphan a
    assert len(errors) == 1


class _DummyPolicy:
    def check(self, req: CheckRequest) -> CheckResponse:
        return CheckResponse(True, "ok")

    def list_verdicts(self) -> tuple[VerdictView, ...]:
        return ()


def test_new_closes_already_built_deps_on_partial_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []
    spy = _Spy("linkpolicy", order)

    def fake_build(cfg: LinkPolicyConfig) -> tuple[Client, Closeable]:
        return _DummyPolicy(), spy

    monkeypatch.setattr(linkpolicy_wire, "build", fake_build)

    # linkpolicy builds (spy pushed), then campaign fails on its absent coordinate.
    with pytest.raises(DomainError):
        new(Config(campaign=CampaignConfig(""), linkpolicy=LinkPolicyConfig("memory")))
    assert spy.closed, "the already-built linkpolicy resource was not cleaned up"
