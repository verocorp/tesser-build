from __future__ import annotations

import typing

import tesser.application as ts

import repo.application.ports.repo_reader as repo_reader
import repo.domain.rules as domain


@ts.do_not_use_function
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


@ts.do_not_use_function
def report(
    read: repo_reader.ReadRepoResponse,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    built = repo(read)
    return (
        tuple(str(problem.text()) for problem in built.problems()),
        tuple(str(count) for count in built.counts()),
    )


@ts.do_not_use_function
def trees(read: repo_reader.ReadRepoResponse) -> tuple[str, ...]:
    return tuple(str(tree) for tree in repo(read).trees())


@ts.do_not_use_function
def _file(record: repo_reader.FileRecord) -> tuple[str, str]:
    return (_state(record.state), record.text)


@ts.do_not_use_function
def _manifest(
    record: repo_reader.ManifestRecord,
) -> tuple[str, tuple[tuple[str, str], ...], str]:
    rows = tuple((row.key, row.kind) for row in record.rows)
    return (_manifest_state(record.state), rows, record.note)


@ts.do_not_use_function
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


@ts.do_not_use_function
def _entries(records: tuple[repo_reader.EntryRecord, ...]) -> tuple[tuple[str, str], ...]:
    return tuple((record.name, _form(record.form)) for record in records)


@ts.do_not_use_function
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


@ts.do_not_use_function
def _form(form: repo_reader.EntryForm) -> str:
    match form:
        case repo_reader.EntryForm.DIRECTORY:
            return domain.DIRECTORY
        case repo_reader.EntryForm.SYMLINK:
            return domain.SYMLINK
        case _ as unreachable:
            typing.assert_never(unreachable)
