from __future__ import annotations

import typing

import tesser.context as ts


class Item(ts.Response):

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class AddItemRequest(ts.Request):

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class AddItemResponse(ts.Response):

    def __init__(self, items: tuple[Item, ...], reason: str) -> None:
        self.items = items
        self.reason = reason


class GetItemRequest(ts.Request):

    def __init__(self, id: str) -> None:
        self.id = id


class GetItemResponse(ts.Response):

    def __init__(self, items: tuple[Item, ...]) -> None:
        self.items = items


class ListItemsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class ListItemsResponse(ts.Response):

    def __init__(self, items: tuple[Item, ...]) -> None:
        self.items = items


class CatalogClient(ts.Client, typing.Protocol):

    def add(self, add_item_request: AddItemRequest) -> AddItemResponse: ...

    def get(self, get_item_request: GetItemRequest) -> GetItemResponse: ...

    def list(self, list_items_request: ListItemsRequest) -> ListItemsResponse: ...
