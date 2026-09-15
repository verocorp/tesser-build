from __future__ import annotations

import typing

import tesser.application as ts


class FileRecord(ts.Request):

    def __init__(self, path: str, text: str) -> None:
        self.path = path
        self.text = text


class WriteTreeRequest(ts.Request):

    def __init__(self, out_dir: str, files: tuple[FileRecord, ...]) -> None:
        self.out_dir = out_dir
        self.files = files


class WriteTreeResponse(ts.Response):

    def __init__(self, paths: tuple[str, ...]) -> None:
        self.paths = paths


class TreeWriter(ts.Port, typing.Protocol):

    def write_tree(self, write_tree_request: WriteTreeRequest) -> WriteTreeResponse: ...
