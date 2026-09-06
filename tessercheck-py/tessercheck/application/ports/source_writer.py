from __future__ import annotations

import typing

import tesser.application as ts


class RewrittenSource(ts.Request):

    def __init__(self, path: str, text: str) -> None:
        self.path = path
        self.text = text


class WriteSourcesRequest(ts.Request):

    def __init__(self, tree: str, sources: tuple[RewrittenSource, ...]) -> None:
        self.tree = tree
        self.sources = sources


class WriteSourcesResponse(ts.Response):

    def __init__(self, written: int) -> None:
        self.written = written


class SourceWriter(ts.Port, typing.Protocol):

    def write(self, write_sources_request: WriteSourcesRequest) -> WriteSourcesResponse: ...
