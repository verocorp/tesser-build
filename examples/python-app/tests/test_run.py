from __future__ import annotations

import threading

import pytest
import tesser.testing as ts

from lifecycle import Host
from srv.run import run_until_signal
from tests.support import SpyApp


@ts.fake
class FakeHostReturning(Host):
    def run(self, stop: threading.Event) -> None:
        return


@ts.fake
class FakeHostRaising(Host):
    def run(self, stop: threading.Event) -> None:
        raise RuntimeError("serve loop crashed")


def test_close_runs_when_host_returns(restore_signals: None) -> None:
    app = SpyApp()
    run_until_signal(FakeHostReturning(), app)
    assert app.closed == 1


def test_close_runs_when_host_raises(restore_signals: None) -> None:
    app = SpyApp()
    with pytest.raises(RuntimeError):
        run_until_signal(FakeHostRaising(), app)
    assert app.closed == 1
