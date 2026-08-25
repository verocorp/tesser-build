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
            case _ as unreadable_manifest:
                typing.assert_never(unreadable_manifest)
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
                case _ as unreadable_file:
                    typing.assert_never(unreadable_file)
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
                case _ as unreadable_declaration:
                    typing.assert_never(unreadable_declaration)
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
                    case _ as unreadable_entry:
                        typing.assert_never(unreadable_entry)
                listed.append((entry_record.name, entry_form))
            listings.append(tuple(listed))
        top, examples = listings
        super().__init__(
            manifest=(manifest_state, manifest_rows, read.manifest.note),
            verify=(verify_state, read.verify.text),
            workflow=(workflow_state, read.workflow.text),
            top=top,
            examples=examples,
            declarations=tuple(declared),
            requirements=read.requirements,
        )
