from __future__ import annotations

import enum
import typing

import tesser.application as ts


class FindWidgetOutcome(enum.Enum):
    YES = "yes"
    NO = "no"


class SaveWidgetRequest(ts.Request):

    def __init__(self, name: str, standing: str) -> None:
        self.name = name
        self.standing = standing


class SaveWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class FindWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class FindWidgetResponse(ts.Response):

    def __init__(self, outcome: FindWidgetOutcome) -> None:
        self.outcome = outcome


class WidgetRepository(ts.Port, typing.Protocol):

    async def save_widget(self, save_widget_request: SaveWidgetRequest) -> SaveWidgetResponse: ...

    async def find_widget(self, find_widget_request: FindWidgetRequest) -> FindWidgetResponse: ...


class WidgetStore(ts.Store, typing.Protocol):

    def transaction(self) -> typing.AsyncContextManager[WidgetRepository]: ...
