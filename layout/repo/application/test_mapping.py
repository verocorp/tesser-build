from __future__ import annotations

import repo.application.mapping as mapping
import repo.application.ports.repo_reader as repo_reader
import repo.domain.rules as domain


def test_every_file_state_maps_to_its_domain_constant() -> None:
    states = (
        repo_reader.FileState.READ,
        repo_reader.FileState.MISSING,
        repo_reader.FileState.UNREADABLE,
    )
    mapped = tuple(
        mapping.MapToFileState(
            file_record=repo_reader.FileRecord(state=state, text="body")
        ).state
        for state in states
    )
    assert mapped == (domain.READ, domain.MISSING, domain.UNREADABLE)


def test_a_file_mapper_carries_the_text_the_reader_gave() -> None:
    record = repo_reader.FileRecord(state=repo_reader.FileState.READ, text="body")
    mapper = mapping.MapToFileState(file_record=record)
    assert mapper.text == "body"


def test_every_manifest_state_maps_to_its_domain_constant() -> None:
    states = (
        repo_reader.ManifestState.READ,
        repo_reader.ManifestState.MISSING,
        repo_reader.ManifestState.UNREADABLE,
        repo_reader.ManifestState.MALFORMED,
        repo_reader.ManifestState.MISSHAPEN,
    )
    mapped = tuple(
        mapping.MapToManifestState(
            manifest_record=repo_reader.ManifestRecord(state=state, rows=(), note="note")
        ).state
        for state in states
    )
    assert mapped == (
        domain.READ,
        domain.MISSING,
        domain.UNREADABLE,
        domain.MALFORMED,
        domain.MISSHAPEN,
    )


def test_a_manifest_mapper_carries_the_rows_and_note_the_reader_gave() -> None:
    row = repo_reader.RowRecord(key="layout", kind=domain.KIND_APP)
    record = repo_reader.ManifestRecord(
        state=repo_reader.ManifestState.READ, rows=(row,), note="note"
    )
    mapper = mapping.MapToManifestState(manifest_record=record)
    assert mapper.rows == (row,)
    assert mapper.note == "note"


def test_every_declaration_state_maps_to_its_domain_constant() -> None:
    states = (
        repo_reader.FileState.READ,
        repo_reader.FileState.MISSING,
        repo_reader.FileState.UNREADABLE,
    )
    mapped = tuple(
        mapping.MapToDeclarationState(
            declaration_record=repo_reader.DeclarationRecord(
                path=domain.DECLARATION, state=state, text="body"
            )
        ).state
        for state in states
    )
    assert mapped == (domain.READ, domain.MISSING, domain.UNREADABLE)


def test_a_declaration_mapper_carries_the_path_and_text_the_reader_gave() -> None:
    record = repo_reader.DeclarationRecord(
        path=domain.DECLARATION, state=repo_reader.FileState.READ, text="body"
    )
    mapper = mapping.MapToDeclarationState(declaration_record=record)
    assert mapper.path == domain.DECLARATION
    assert mapper.text == "body"


def test_every_entry_form_maps_to_its_domain_constant() -> None:
    forms = (repo_reader.EntryForm.DIRECTORY, repo_reader.EntryForm.SYMLINK)
    mapped = tuple(
        mapping.MapToEntryForm(
            entry_record=repo_reader.EntryRecord(name="examples", form=form)
        ).form
        for form in forms
    )
    assert mapped == (domain.DIRECTORY, domain.SYMLINK)


def test_an_entry_mapper_carries_the_name_the_reader_gave() -> None:
    record = repo_reader.EntryRecord(name="examples", form=repo_reader.EntryForm.SYMLINK)
    mapper = mapping.MapToEntryForm(entry_record=record)
    assert mapper.name == "examples"
