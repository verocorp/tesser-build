from __future__ import annotations

from typing import Protocol

import tesser.context as ts


class ItemView(ts.Response):

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class AddItemRequest(ts.Request):

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class AddItemResponse(ts.Response):

    def __init__(self, id: str, name: str, reason: str) -> None:
        self.id = id
        self.name = name
        self.reason = reason


class GetItemRequest(ts.Request):

    def __init__(self, id: str) -> None:
        self.id = id


class GetItemResponse(ts.Response):

    def __init__(self, items: tuple[ItemView, ...]) -> None:
        self.items = items


class ListItemsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class ListItemsResponse(ts.Response):

    def __init__(self, items: tuple[ItemView, ...]) -> None:
        self.items = items


class CatalogClient(ts.Client, Protocol):

    def add(self, request: AddItemRequest) -> AddItemResponse: ...

    def get(self, request: GetItemRequest) -> GetItemResponse: ...

    def list(self, request: ListItemsRequest) -> ListItemsResponse: ...
