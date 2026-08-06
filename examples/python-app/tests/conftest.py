from __future__ import annotations

import signal
from collections.abc import Iterator

import pytest


@pytest.fixture
def restore_signals() -> Iterator[None]:
    orig_int = signal.getsignal(signal.SIGINT)
    orig_term = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGINT, orig_int)
    signal.signal(signal.SIGTERM, orig_term)
