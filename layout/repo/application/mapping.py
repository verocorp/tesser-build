from __future__ import annotations

import typing

import tesser.application as ts

import repo.application.ports.repo_reader as repo_reader
import repo.domain.rules as domain


class MapToRepoSpec(ts.Mapper, domain.RepoSpec):

    def __init__(self, read: repo_reader.ReadRepoResponse) -> None:
        match read.manifest.state:
            case repo_reader.ManifestState.READ:
                manifest_state = domain.READ
            case repo_reader.ManifestState.MISSING:
                manifest_state = domain.MISSING
            case repo_reader.ManifestState.UNREADABLE:
                manifest_state = domain.UNREADABLE
            case repo_reader.ManifestState.MALFORMED:
                manifest_state = domain.MALFORMED
            case repo_reader.ManifestState.MISSHAPEN:
                manifest_state = domain.MISSHAPEN
            case _ as unreachable_manifest:
                typing.assert_never(unreachable_manifest)
        manifest_rows = tuple((row.key, row.kind) for row in read.manifest.rows)
        file_states: list[str] = []
        for file_record in (read.verify, read.workflow):
            match file_record.state:
                case repo_reader.FileState.READ:
                    file_states.append(domain.READ)
                case repo_reader.FileState.MISSING:
                    file_states.append(domain.MISSING)
                case repo_reader.FileState.UNREADABLE:
                    file_states.append(domain.UNREADABLE)
                case _ as unreachable_file:
                    typing.assert_never(unreachable_file)
        verify_state, workflow_state = file_states
        declared: list[tuple[str, str, str]] = []
        for declaration_record in read.declarations:
            match declaration_record.state:
                case repo_reader.FileState.READ:
                    declaration_state = domain.READ
                case repo_reader.FileState.MISSING:
                    declaration_state = domain.MISSING
                case repo_reader.FileState.UNREADABLE:
                    declaration_state = domain.UNREADABLE
                case _ as unreachable_declaration:
                    typing.assert_never(unreachable_declaration)
            declared.append(
                (declaration_record.path, declaration_state, declaration_record.text)
            )
        listings: list[tuple[tuple[str, str], ...]] = []
        for entry_records in (read.top, read.examples):
            listed: list[tuple[str, str]] = []
            for entry_record in entry_records:
                match entry_record.form:
                    case repo_reader.EntryForm.DIRECTORY:
                        entry_form = domain.DIRECTORY
                    case repo_reader.EntryForm.SYMLINK:
                        entry_form = domain.SYMLINK
                    case _ as unreachable_entry:
                        typing.assert_never(unreachable_entry)
                listed.append((entry_record.name, entry_form))
            listings.append(tuple(listed))
        top, examples = listings
        stated: list[tuple[str, str, str, str]] = []
        for floor_record in read.floors:
            match floor_record.key:
                case repo_reader.FloorKey.REQUIRES_PYTHON:
                    floor_key = domain.REQUIRES_PYTHON
                case repo_reader.FloorKey.TARGET_VERSION:
                    floor_key = domain.TARGET_VERSION
                case _ as unreachable_key:
                    typing.assert_never(unreachable_key)
            match floor_record.state:
                case repo_reader.FloorState.READ:
                    floor_state = domain.READ
                case repo_reader.FloorState.UNDECLARED:
                    floor_state = domain.UNDECLARED
                case repo_reader.FloorState.UNREADABLE:
                    floor_state = domain.UNREADABLE
                case repo_reader.FloorState.MALFORMED:
                    floor_state = domain.MALFORMED
                case _ as unreachable_floor:
                    typing.assert_never(unreachable_floor)
            stated.append(
                (floor_record.path, floor_key, floor_state, floor_record.value)
            )
        super().__init__(
            manifest=(manifest_state, manifest_rows, read.manifest.note),
            verify=(verify_state, read.verify.text),
            workflow=(workflow_state, read.workflow.text),
            top=top,
            examples=examples,
            declarations=tuple(declared),
            requirements=read.requirements,
            floors=tuple(stated),
        )
