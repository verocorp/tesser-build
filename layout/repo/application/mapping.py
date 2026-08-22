from __future__ import annotations

import typing

import tesser.application as ts

import repo.application.ports.repo_reader as repo_reader
import repo.domain.rules as domain


class MapToManifestState(ts.Mapper):

    def __init__(self, manifest_record: repo_reader.ManifestRecord) -> None:
        match manifest_record.state:
            case repo_reader.ManifestState.READ:
                self._state = domain.READ
            case repo_reader.ManifestState.MISSING:
                self._state = domain.MISSING
            case repo_reader.ManifestState.UNREADABLE:
                self._state = domain.UNREADABLE
            case repo_reader.ManifestState.MALFORMED:
                self._state = domain.MALFORMED
            case repo_reader.ManifestState.MISSHAPEN:
                self._state = domain.MISSHAPEN
            case _ as unreachable:
                typing.assert_never(unreachable)
        self._rows = manifest_record.rows
        self._note = manifest_record.note

    @property
    def state(self) -> str:
        return self._state

    @property
    def rows(self) -> tuple[repo_reader.RowRecord, ...]:
        return self._rows

    @property
    def note(self) -> str:
        return self._note


class MapToFileState(ts.Mapper):

    def __init__(self, file_record: repo_reader.FileRecord) -> None:
        match file_record.state:
            case repo_reader.FileState.READ:
                self._state = domain.READ
            case repo_reader.FileState.MISSING:
                self._state = domain.MISSING
            case repo_reader.FileState.UNREADABLE:
                self._state = domain.UNREADABLE
            case _ as unreachable:
                typing.assert_never(unreachable)
        self._text = file_record.text

    @property
    def state(self) -> str:
        return self._state

    @property
    def text(self) -> str:
        return self._text


class MapToDeclarationState(ts.Mapper):

    def __init__(self, declaration_record: repo_reader.DeclarationRecord) -> None:
        match declaration_record.state:
            case repo_reader.FileState.READ:
                self._state = domain.READ
            case repo_reader.FileState.MISSING:
                self._state = domain.MISSING
            case repo_reader.FileState.UNREADABLE:
                self._state = domain.UNREADABLE
            case _ as unreachable:
                typing.assert_never(unreachable)
        self._path = declaration_record.path
        self._text = declaration_record.text

    @property
    def path(self) -> str:
        return self._path

    @property
    def state(self) -> str:
        return self._state

    @property
    def text(self) -> str:
        return self._text


class MapToEntryForm(ts.Mapper):

    def __init__(self, entry_record: repo_reader.EntryRecord) -> None:
        match entry_record.form:
            case repo_reader.EntryForm.DIRECTORY:
                self._form = domain.DIRECTORY
            case repo_reader.EntryForm.SYMLINK:
                self._form = domain.SYMLINK
            case _ as unreachable:
                typing.assert_never(unreachable)
        self._name = entry_record.name

    @property
    def name(self) -> str:
        return self._name

    @property
    def form(self) -> str:
        return self._form
