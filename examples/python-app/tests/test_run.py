from __future__ import annotations

import signal
import threading
from collections.abc import Iterator

import pytest

from srv.run import run_until_signal


@pytest.fixture(autouse=True)
def _restore_signals() -> Iterator[None]:
    orig_int = signal.getsignal(signal.SIGINT)
    orig_term = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGINT, orig_int)
    signal.signal(signal.SIGTERM, orig_term)


class _SpyApp:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


class _ReturningHost:
    def run(self, stop: threading.Event) -> None:
        return


class _RaisingHost:
    def run(self, stop: threading.Event) -> None:
        raise RuntimeError("serve loop crashed")


def test_close_runs_when_host_returns() -> None:
    app = _SpyApp()
    run_until_signal(_ReturningHost(), app)
    assert app.closed == 1


def test_close_runs_when_host_raises() -> None:
    app = _SpyApp()
    with pytest.raises(RuntimeError):
        run_until_signal(_RaisingHost(), app)
    assert app.closed == 1
