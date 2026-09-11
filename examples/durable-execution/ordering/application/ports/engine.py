from __future__ import annotations  # tesser:debt TB052

import tesser.application as ts


class EngineRejected(ts.Error):

    def __init__(self, message: str) -> None:
        self.message = message


class EngineMissing(ts.Error):

    def __init__(self, message: str) -> None:
        self.message = message


class EngineConflict(ts.Error):

    def __init__(self, message: str) -> None:
        self.message = message


class EngineUnavailable(ts.Error):

    def __init__(self, message: str) -> None:
        self.message = message
