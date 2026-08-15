from __future__ import annotations

import typing

import tesser.application as ts

import repo.application.ports.repo_reader as repo_reader
import repo.domain.rules as domain


@ts.function
def repo(read: repo_reader.ReadRepoResponse) -> domain.Repo:
    return domain.Repo(
        domain.RepoSpec(
            manifest=_manifest(read.manifest),
            verify=_file(read.verify),
            workflow=_file(read.workflow),
            top=_entries(read.top),
            examples=_entries(read.examples),
            declarations=tuple(
                (record.path, _state(record.state), record.text)
                for record in read.declarations
            ),
            requirements=read.requirements,
        )
    )


@ts.function
def problems(read: repo_reader.ReadRepoResponse) -> tuple[str, ...]:
    return tuple(str(problem.text()) for problem in repo(read).problems())


@ts.function
def trees(read: repo_reader.ReadRepoResponse) -> tuple[str, ...]:
    return tuple(str(tree) for tree in repo(read).trees())


@ts.function
def counts(read: repo_reader.ReadRepoResponse) -> tuple[str, ...]:
    return tuple(str(count) for count in repo(read).counts())


@ts.function
def _file(record: repo_reader.FileRecord) -> tuple[str, str]:
    return (_state(record.state), record.text)


@ts.function
def _manifest(
    record: repo_reader.ManifestRecord,
) -> tuple[str, tuple[tuple[str, str], ...], str]:
    rows = tuple((row.key, row.kind) for row in record.rows)
    return (_manifest_state(record.state), rows, record.note)


@ts.function
def _manifest_state(state: repo_reader.ManifestState) -> str:
    match state:
        case repo_reader.ManifestState.READ:
            return domain.READ
        case repo_reader.ManifestState.MISSING:
            return domain.MISSING
        case repo_reader.ManifestState.UNREADABLE:
            return domain.UNREADABLE
        case repo_reader.ManifestState.MALFORMED:
            return domain.MALFORMED
        case repo_reader.ManifestState.MISSHAPEN:
            return domain.MISSHAPEN
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.function
def _entries(records: tuple[repo_reader.EntryRecord, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((record.name, _form(record.form)) for record in records)


@ts.function
def _state(state: repo_reader.FileState) -> str:
    match state:
        case repo_reader.FileState.READ:
            return domain.READ
        case repo_reader.FileState.MISSING:
            return domain.MISSING
        case repo_reader.FileState.UNREADABLE:
            return domain.UNREADABLE
        case _ as unreachable:
            typing.assert_never(unreachable)


@ts.function
def _form(form: repo_reader.EntryForm) -> str:
    match form:
        case repo_reader.EntryForm.DIRECTORY:
            return domain.DIRECTORY
        case repo_reader.EntryForm.SYMLINK:
            return domain.SYMLINK
        case _ as unreachable:
            typing.assert_never(unreachable)
