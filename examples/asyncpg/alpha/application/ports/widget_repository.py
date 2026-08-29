from __future__ import annotations

import enum
import typing

import tesser.application as ts


class Found(enum.Enum):
    YES = "yes"
    NO = "no"


class SaveWidgetRequest(ts.Request):

    def __init__(self, name: str, part: str) -> None:
        self.name = name
        self.part = part


class SaveWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class LoadWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class LoadWidgetResponse(ts.Response):

    def __init__(self, name: str, part: str) -> None:
        self.name = name
        self.part = part


class FindWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class FindWidgetResponse(ts.Response):

    def __init__(self, found: Found) -> None:
        self.found = found


class WidgetRepository(ts.Port, typing.Protocol):

    async def save_widget(self, request: SaveWidgetRequest) -> SaveWidgetResponse: ...

    async def load_widget(self, request: LoadWidgetRequest) -> LoadWidgetResponse: ...

    async def find_widget(self, request: FindWidgetRequest) -> FindWidgetResponse: ...


class WidgetStore(ts.Port, typing.Protocol):  # tesser:debt TB052

    def transaction(self) -> typing.AsyncContextManager[WidgetRepository]: ...  # tesser:debt TB081
