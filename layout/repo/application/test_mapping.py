from __future__ import annotations

import tesser.testing as ts

import repo.application.mapping as mapping
import repo.application.ports.repo_reader as repo_reader
import repo.domain.rules as domain


@ts.helper
def _empty_response(  # tessercheck:ignore TB073
    note: str = "",
) -> repo_reader.ReadRepoResponse:
    return repo_reader.ReadRepoResponse(
        manifest=repo_reader.ManifestRecord(
            state=repo_reader.ManifestState.MALFORMED, rows=(), note=note
        ),
        verify=repo_reader.FileRecord(state=repo_reader.FileState.MISSING, text=""),
        workflow=repo_reader.FileRecord(state=repo_reader.FileState.MISSING, text=""),
        top=(),
        examples=(),
        declarations=(),
        requirements=(),
    )


def test_every_file_state_maps_to_its_domain_constant() -> None:
    assert mapping._state(repo_reader.FileState.READ) == domain.READ
    assert mapping._state(repo_reader.FileState.MISSING) == domain.MISSING
    assert mapping._state(repo_reader.FileState.UNREADABLE) == domain.UNREADABLE


def test_every_manifest_state_maps_to_its_domain_constant() -> None:
    assert mapping._manifest_state(repo_reader.ManifestState.READ) == domain.READ
    assert mapping._manifest_state(repo_reader.ManifestState.MISSING) == domain.MISSING
    assert (
        mapping._manifest_state(repo_reader.ManifestState.UNREADABLE)
        == domain.UNREADABLE
    )
    assert (
        mapping._manifest_state(repo_reader.ManifestState.MALFORMED) == domain.MALFORMED
    )
    assert (
        mapping._manifest_state(repo_reader.ManifestState.MISSHAPEN) == domain.MISSHAPEN
    )


def test_every_entry_form_maps_to_its_domain_constant() -> None:
    assert mapping._form(repo_reader.EntryForm.DIRECTORY) == domain.DIRECTORY
    assert mapping._form(repo_reader.EntryForm.SYMLINK) == domain.SYMLINK


def test_a_manifest_record_carries_rows_and_note_into_the_spec_shape() -> None:
    record = repo_reader.ManifestRecord(
        state=repo_reader.ManifestState.READ,
        rows=(repo_reader.RowRecord(key="appone", kind="app"),),
        note="",
    )
    assert mapping._manifest(record) == (domain.READ, (("appone", "app"),), "")


def test_entries_carry_name_and_form() -> None:
    records = (
        repo_reader.EntryRecord(name="docs", form=repo_reader.EntryForm.DIRECTORY),
        repo_reader.EntryRecord(name="vendored", form=repo_reader.EntryForm.SYMLINK),
    )
    assert mapping._entries(records) == (
        ("docs", domain.DIRECTORY),
        ("vendored", domain.SYMLINK),
    )


def test_report_renders_problems_and_counts_as_text() -> None:
    problems, counts = mapping.report(_empty_response(note="line 1 column 2"))
    assert problems == ("manifest.json is unreadable: line 1 column 2",)
    assert counts == ("0", "0")


def test_trees_render_as_text_and_degrade_with_the_manifest() -> None:
    assert mapping.trees(_empty_response()) == ()
