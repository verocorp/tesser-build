from __future__ import annotations

import enum
import typing

import tesser.application as ts


class RootForm(enum.Enum):
    APP = "app"
    MISSING = "missing"
    UNREADABLE = "unreadable"
    UNRECOGNIZED = "unrecognized"


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

    def __init__(self, tree: str) -> None:
        self.tree = tree


class ReadSourcesResponse(ts.Response):

    def __init__(
        self,
        root: RootForm,
        nested: tuple[str, ...],
        symlinked: tuple[str, ...],
        sources: tuple[SourceFile, ...],
        exports: tuple[str, ...],
        imports: tuple[str, ...],
        stdlib: tuple[str, ...],
        pure_stdlib: tuple[str, ...],
    ) -> None:
        self.root = root
        self.nested = nested
        self.symlinked = symlinked
        self.sources = sources
        self.exports = exports
        self.imports = imports
        self.stdlib = stdlib
        self.pure_stdlib = pure_stdlib


class SourceReader(ts.Port, typing.Protocol):

    def sources(self, request: ReadSourcesRequest) -> ReadSourcesResponse: ...
