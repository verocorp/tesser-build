from __future__ import annotations

import typing

import tesser.application as ts

import repo.application.ports.repo_reader as repo_reader
import repo.domain.rules as domain


@ts.do_not_use_function
def _manifest_state(state: repo_reader.ManifestState) -> str:  # tesser:debt TB051
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
def _state(state: repo_reader.FileState) -> str:  # tesser:debt TB051
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
def _form(form: repo_reader.EntryForm) -> str:  # tesser:debt TB051
    match form:
        case repo_reader.EntryForm.DIRECTORY:
            return domain.DIRECTORY
        case repo_reader.EntryForm.SYMLINK:
            return domain.SYMLINK
        case _ as unreachable:
            typing.assert_never(unreachable)
