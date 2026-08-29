from __future__ import annotations

import typing

import tesser.context as ts


class LinksByVerdictRequest(ts.Request):

    def __init__(self) -> None:
        return None


class LinkVerdictView(ts.Response):

    def __init__(self, slug: str, target_url: str, decision: str, reason: str) -> None:
        self.slug = slug
        self.target_url = target_url
        self.decision = decision
        self.reason = reason


class LinksByVerdictResponse(ts.Response):

    def __init__(self, links: tuple[LinkVerdictView, ...]) -> None:
        self.links = links


class Client(ts.Client, typing.Protocol):

    def links_by_verdict(self, req: LinksByVerdictRequest) -> LinksByVerdictResponse: ...