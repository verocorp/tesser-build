from __future__ import annotations

from typing import Protocol

import tesser.application as ts


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


class FoundItem(ts.Response):

    def __init__(self, item: ItemView) -> None:
        self.item = item


class MissingItem(ts.Response):

    def __init__(self) -> None:
        return None


class ListItemsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class ListItemsResponse(ts.Response):

    def __init__(self, items: tuple[ItemView, ...]) -> None:
        self.items = items


class ItemRepository(ts.Port, Protocol):

    def save(self, request: SaveItemRequest) -> SaveItemResponse: ...

    def find(self, request: FindItemRequest) -> FoundItem | MissingItem: ...

    def all(self, request: ListItemsRequest) -> ListItemsResponse: ...
