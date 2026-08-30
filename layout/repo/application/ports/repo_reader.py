from __future__ import annotations

import enum
import typing

import tesser.application as ts


class FileState(enum.Enum):
    READ = "read"
    MISSING = "missing"
    UNREADABLE = "unreadable"


class ManifestState(enum.Enum):
    READ = "read"
    MISSING = "missing"
    UNREADABLE = "unreadable"
    MALFORMED = "malformed"
    MISSHAPEN = "misshapen"


class RowRecord(ts.Response):

    def __init__(self, key: str, kind: str) -> None:
        self.key = key
        self.kind = kind


class ManifestRecord(ts.Response):

    def __init__(
        self, state: ManifestState, rows: tuple[RowRecord, ...], note: str
    ) -> None:
        self.state = state
        self.rows = rows
        self.note = note


class EntryForm(enum.Enum):
    DIRECTORY = "directory"
    SYMLINK = "symlink"


class FileRecord(ts.Response):

    def __init__(self, state: FileState, text: str) -> None:
        self.state = state
        self.text = text


class EntryRecord(ts.Response):

    def __init__(self, name: str, form: EntryForm) -> None:
        self.name = name
        self.form = form


class DeclarationRecord(ts.Response):

    def __init__(self, path: str, state: FileState, text: str) -> None:
        self.path = path
        self.state = state
        self.text = text


class FloorKey(enum.Enum):
    REQUIRES_PYTHON = "requires-python"
    TARGET_VERSION = "target-version"


class FloorState(enum.Enum):
    READ = "read"
    UNDECLARED = "undeclared"
    UNREADABLE = "unreadable"
    MALFORMED = "malformed"


class FloorRecord(ts.Response):

    def __init__(
        self, path: str, key: FloorKey, state: FloorState, value: str
    ) -> None:
        self.path = path
        self.key = key
        self.state = state
        self.value = value


class ReadRepoRequest(ts.Request):

    def __init__(self, repo_root: str) -> None:
        self.repo_root = repo_root


class ReadRepoResponse(ts.Response):

    def __init__(
        self,
        manifest: ManifestRecord,
        verify: FileRecord,
        workflow: FileRecord,
        top: tuple[EntryRecord, ...],
        examples: tuple[EntryRecord, ...],
        declarations: tuple[DeclarationRecord, ...],
        requirements: tuple[str, ...],
        floors: tuple[FloorRecord, ...],
    ) -> None:
        self.manifest = manifest
        self.verify = verify
        self.workflow = workflow
        self.top = top
        self.examples = examples
        self.declarations = declarations
        self.requirements = requirements
        self.floors = floors


class RepoReader(ts.Port, typing.Protocol):

    def read(self, request: ReadRepoRequest) -> ReadRepoResponse: ...
