from __future__ import annotations

from typing import Protocol

import tesser.application as ts

# SPLIT variant (contrast with examples/spike-ports/cardinality): the
# two-outcome answer of "does this item exist" is expressed as two port
# methods instead of one cardinality-carrying response.
#
#   exists(ItemExistsRequest) -> ItemExistsResponse   # the existence question
#   get(GetItemRequest)       -> GetItemResponse      # the retrieval question
#
# get() is only legal to call for an id that exists() has just answered True
# for. Every port method must return exactly one ts.Response subclass — no
# Optional, no union — so an adapter cannot express "no item" by returning a
# hollow/zero-valued GetItemResponse either: a GetItemResponse with id="",
# name="" would be indistinguishable from a real (if oddly-named) item, and
# would silently pass validation-free through to a caller who forgot the
# exists() check. We chose the other option: get() raises ItemNotFoundError
# when called for an absent id. That makes "you skipped the check" a loud,
# immediate failure instead of a bogus value quietly flowing downstream, and
# it matches the precondition language above ("only legal to call when
# exists() said True") — calling it otherwise is a contract violation, not a
# normal outcome to encode in the return type. Every adapter (the in-memory
# gateway and the test fake) implements this the same way; see the assertion
# in catalog/tests/test_catalog.py.
#
# The cost of this design lives at the call site: between the exists() call
# and the get() call there is a window — check-then-act — during which, for
# any adapter backed by a real external store, the item could be removed.
# The in-memory adapter here is single-threaded and never observes that
# window, so ItemNotFoundError never actually fires in this example's tests
# outside the one that calls get() directly on a never-populated id. But the
# port's shape is written as though the window were real, because for any
# adapter that talks to a database or network service, it would be.


class ItemNotFoundError(Exception):
    """Raised by get() when called for an id exists() did not just confirm."""


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


class ItemExistsRequest(ts.Request):

    def __init__(self, id: str) -> None:
        self.id = id


class ItemExistsResponse(ts.Response):

    def __init__(self, exists: bool) -> None:
        self.exists = exists


class GetItemRequest(ts.Request):

    def __init__(self, id: str) -> None:
        self.id = id


class GetItemResponse(ts.Response):

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name


class ListItemsRequest(ts.Request):

    def __init__(self) -> None:
        return None


class ListItemsResponse(ts.Response):

    def __init__(self, items: tuple[ItemView, ...]) -> None:
        self.items = items


class ItemRepository(ts.Port, Protocol):

    def save(self, request: SaveItemRequest) -> SaveItemResponse: ...

    def exists(self, request: ItemExistsRequest) -> ItemExistsResponse: ...

    def get(self, request: GetItemRequest) -> GetItemResponse: ...

    def all(self, request: ListItemsRequest) -> ListItemsResponse: ...
