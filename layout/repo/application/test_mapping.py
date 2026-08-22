from __future__ import annotations

import repo.application.mapping as mapping
import repo.application.ports.repo_reader as repo_reader
import repo.domain.rules as domain


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
