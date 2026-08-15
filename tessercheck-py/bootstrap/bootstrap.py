from __future__ import annotations

import tesser.context as ts

import tessercheck.client.client as tessercheck_client
import tessercheck.wiring.wire as tessercheck_wire

from bootstrap.config import Config
from tesser.lifecycle import Closeable


class App:  # tessercheck:ignore TB051

    def __init__(self, check_client: tessercheck_client.Client, closeable: Closeable) -> None:
        self.tessercheck = check_client
        self._closeable = closeable
        self._closed = False

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._closeable.close()


@ts.function
def new(cfg: Config) -> App:
    check_client, closeable = tessercheck_wire.build(cfg.tessercheck)
    return App(check_client, closeable)
