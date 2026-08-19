from __future__ import annotations

from typing import Protocol

import tesser.application as ts


class TestModuleText(ts.Response):

    def __init__(self, name: str, text: str) -> None:
        self.name = name
        self.text = text


class ReadRulebookRequest(ts.Request):

    def __init__(self, tree: str) -> None:
        self.tree = tree


class ReadRulebookResponse(ts.Response):

    def __init__(
        self,
        checks_text: str,
        test_modules: tuple[TestModuleText, ...],
        contracts_text: str,
    ) -> None:
        self.checks_text = checks_text
        self.test_modules = test_modules
        self.contracts_text = contracts_text


class RulebookSources(ts.Port, Protocol):

    def read(self, request: ReadRulebookRequest) -> ReadRulebookResponse: ...
