from __future__ import annotations

import enum
from typing import Protocol

import tesser.application as ts


class RootForm(enum.Enum):
    APP = "app"
    MISSING = "missing"
    UNREADABLE = "unreadable"
    UNRECOGNIZED = "unrecognized"
    DOUBLE_EXPORT = "double-export"


class SourceState(enum.Enum):
    READ = "read"
    UNREADABLE = "unreadable"


class ModuleForm(enum.Enum):
    PACKAGE = "package"
    MODULE = "module"


class SourceFile(ts.Response):

    def __init__(
        self, path: str, name: str, text: str, state: SourceState, form: ModuleForm
    ) -> None:
        self.path = path
        self.name = name
        self.text = text
        self.state = state
        self.form = form


class ReadSourcesRequest(ts.Request):

    def __init__(self, root: str) -> None:
        self.root = root


class ReadSourcesResponse(ts.Response):

    def __init__(
        self,
        root: RootForm,
        nested: tuple[str, ...],
        symlinked: tuple[str, ...],
        sources: tuple[SourceFile, ...],
        export: str,
        imports: tuple[str, ...],
    ) -> None:
        self.root = root
        self.nested = nested
        self.symlinked = symlinked
        self.sources = sources
        self.export = export
        self.imports = imports


class SourceReader(ts.Port, Protocol):

    def sources(self, request: ReadSourcesRequest) -> ReadSourcesResponse: ...
