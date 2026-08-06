from __future__ import annotations

import tesser.context as ts


class Config(ts.Wiring):

    def __init__(self, storage: str) -> None:
        self.storage = storage
