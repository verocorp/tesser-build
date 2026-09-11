from __future__ import annotations

import enum
import typing

import tesser.application as ts


class Found(enum.Enum):
    YES = "yes"
    NO = "no"


class Added(enum.Enum):
    ADDED = "added"
    EXISTS = "exists"


class Loaded(enum.Enum):
    FOUND = "found"
    MISSING = "missing"


class StoreUnavailable(ts.Error):
    pass


class AddWidgetRequest(ts.Request):

    def __init__(self, name: str, part: str, standing: str) -> None:
        self.name = name
        self.part = part
        self.standing = standing


class AddWidgetResponse(ts.Response):

    def __init__(self, outcome: Added, name: str) -> None:
        self.outcome = outcome
        self.name = name


class SaveWidgetRequest(ts.Request):

    def __init__(self, name: str, part: str, standing: str) -> None:
        self.name = name
        self.part = part
        self.standing = standing


class SaveWidgetResponse(ts.Response):

    def __init__(self, name: str) -> None:
        self.name = name


class LoadWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class WidgetRecord(ts.Response):

    def __init__(self, name: str, part: str, standing: str) -> None:
        self.name = name
        self.part = part
        self.standing = standing


class LoadWidgetResponse(ts.Response):

    def __init__(self, outcome: Loaded, widgets: tuple[WidgetRecord, ...]) -> None:
        self.outcome = outcome
        self.widgets = widgets


class FindWidgetRequest(ts.Request):

    def __init__(self, name: str) -> None:
        self.name = name


class FindWidgetResponse(ts.Response):

    def __init__(self, found: Found) -> None:
        self.found = found


class WidgetRepository(ts.Port, typing.Protocol):

    async def add_widget(self, add_widget_request: AddWidgetRequest) -> AddWidgetResponse: ...

    async def save_widget(self, save_widget_request: SaveWidgetRequest) -> SaveWidgetResponse: ...

    async def load_widget(self, load_widget_request: LoadWidgetRequest) -> LoadWidgetResponse: ...

    async def find_widget(self, find_widget_request: FindWidgetRequest) -> FindWidgetResponse: ...


class WidgetStore(ts.Store, typing.Protocol):

    def transaction(self) -> typing.AsyncContextManager[WidgetRepository]: ...
