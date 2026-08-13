from __future__ import annotations  # tessercheck:ignore-file TB040

from typing import Protocol

import tesser.application as ts


class Closeable(ts.Port, Protocol):
    def close(self) -> None: ...
