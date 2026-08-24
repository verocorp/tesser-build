from __future__ import annotations

import enum
import typing

import tesser.application as ts


class ItemLookup(enum.Enum):
    FOUND = "found"
    ARCHIVED = "archived"
    MISSING = "missing"


class ItemView(ts.Response):

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class SaveItemRequest(ts.Request):

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class SaveItemResponse(ts.Response):

    def __init__(self) -> None:
        return None


class FindItemRequest(ts.Request):

    def __init__(self, id: str) -> None:
        self.id = id


class FindItemResponse(ts.Response):

    def __init__(self, outcome: ItemLookup, items: tuple[ItemView, ...]) -> None:
        self.outcome = outcome
        self.items = items


class ListItemsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class ListItemsResponse(ts.Response):

    def __init__(self, items: tuple[ItemView, ...]) -> None:
        self.items = items


class ItemRepository(ts.Port, typing.Protocol):

    def save(self, request: SaveItemRequest) -> SaveItemResponse: ...

    def find(self, request: FindItemRequest) -> FindItemResponse: ...

    def all(self, request: ListItemsRequest) -> ListItemsResponse: ...
