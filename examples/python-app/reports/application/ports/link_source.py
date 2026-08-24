from __future__ import annotations

import typing

import tesser.application as ts


class LinkRecord(ts.Response):

    def __init__(self, slug: str, target_url: str) -> None:
        self.slug = slug
        self.target_url = target_url


class ListLinksRequest(ts.Request):

    def __init__(self) -> None:
        return None


class ListLinksResponse(ts.Response):

    def __init__(self, links: tuple[LinkRecord, ...]) -> None:
        self.links = links


class LinkSource(ts.Port, typing.Protocol):

    def links(self, request: ListLinksRequest) -> ListLinksResponse: ...
