from __future__ import annotations

import signal
import threading

import pytest
import tesser.testing as ts

from protocol.lifecycle import Host
from srv.run import run_until_signal


@ts.fake
class FakeHostReturning(Host):
    def __init__(self) -> None:
        self.runs = 0
        self.stop_was_set = True

    def run(self, stop: threading.Event) -> None:
        self.runs += 1
        self.stop_was_set = stop.is_set()


@ts.fake
class FakeHostRaising(Host):
    def run(self, stop: threading.Event) -> None:
        raise RuntimeError("serve loop crashed")


@ts.fake
class FakeHostCallingTheInstalledHandler(Host):
    def __init__(self, signum: int) -> None:
        self.signum = signum
        self.handler_was_callable = False
        self.stop_was_set = False

    def run(self, stop: threading.Event) -> None:
        handler = signal.getsignal(self.signum)
        self.handler_was_callable = callable(handler)
        if callable(handler):
            handler(self.signum, None)
        self.stop_was_set = stop.is_set()


def test_the_host_runs_once_with_an_unset_stop() -> None:
    original_int = signal.getsignal(signal.SIGINT)
    original_term = signal.getsignal(signal.SIGTERM)
    try:
        closes: list[None] = []
        host = FakeHostReturning()
        run_until_signal(host, lambda: closes.append(None))
        assert host.runs == 1
        assert host.stop_was_set is False
    finally:
        signal.signal(signal.SIGINT, original_int)
        signal.signal(signal.SIGTERM, original_term)


def test_the_app_closes_when_the_host_returns() -> None:
    original_int = signal.getsignal(signal.SIGINT)
    original_term = signal.getsignal(signal.SIGTERM)
    try:
        closes: list[None] = []
        run_until_signal(FakeHostReturning(), lambda: closes.append(None))
        assert len(closes) == 1
    finally:
        signal.signal(signal.SIGINT, original_int)
        signal.signal(signal.SIGTERM, original_term)


def test_the_app_closes_when_the_host_crashes_and_the_crash_still_surfaces() -> None:
    original_int = signal.getsignal(signal.SIGINT)
    original_term = signal.getsignal(signal.SIGTERM)
    try:
        closes: list[None] = []
        with pytest.raises(RuntimeError) as caught:
            run_until_signal(FakeHostRaising(), lambda: closes.append(None))
        assert "serve loop crashed" in str(caught.value)
        assert len(closes) == 1
    finally:
        signal.signal(signal.SIGINT, original_int)
        signal.signal(signal.SIGTERM, original_term)


def test_an_interrupt_signal_sets_the_stop_the_host_waits_on() -> None:
    original_int = signal.getsignal(signal.SIGINT)
    original_term = signal.getsignal(signal.SIGTERM)
    try:
        closes: list[None] = []
        host = FakeHostCallingTheInstalledHandler(signal.SIGINT)
        run_until_signal(host, lambda: closes.append(None))
        assert host.handler_was_callable is True
        assert host.stop_was_set is True
    finally:
        signal.signal(signal.SIGINT, original_int)
        signal.signal(signal.SIGTERM, original_term)


def test_a_termination_signal_sets_the_stop_the_host_waits_on() -> None:
    original_int = signal.getsignal(signal.SIGINT)
    original_term = signal.getsignal(signal.SIGTERM)
    try:
        closes: list[None] = []
        host = FakeHostCallingTheInstalledHandler(signal.SIGTERM)
        run_until_signal(host, lambda: closes.append(None))
        assert host.handler_was_callable is True
        assert host.stop_was_set is True
    finally:
        signal.signal(signal.SIGINT, original_int)
        signal.signal(signal.SIGTERM, original_term)
