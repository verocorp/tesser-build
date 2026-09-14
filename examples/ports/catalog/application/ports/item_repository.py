from __future__ import annotations

import enum
import typing

import tesser.application as ts


class FindItemOutcome(enum.Enum):
    FOUND = "found"
    ARCHIVED = "archived"
    NOT_FOUND = "not_found"


class Item(ts.Response):

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

    def __init__(self, outcome: FindItemOutcome, items: tuple[Item, ...]) -> None:
        self.outcome = outcome
        self.items = items


class ListItemsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class ListItemsResponse(ts.Response):

    def __init__(self, items: tuple[Item, ...]) -> None:
        self.items = items


class ItemRepository(ts.Port, typing.Protocol):

    def save_item(self, save_item_request: SaveItemRequest) -> SaveItemResponse: ...

    def find_item(self, find_item_request: FindItemRequest) -> FindItemResponse: ...

    def list_items(self, list_items_request: ListItemsRequest) -> ListItemsResponse: ...
