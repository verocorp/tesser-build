from __future__ import annotations

import tesser.testing as ts

import repo.application.mapping as mapping
import repo.application.ports.repo_reader as repo_reader
import repo.domain.rules as domain


@ts.helper
def _read(
    manifest_state: str = "read",
    verify_state: str = "read",
    workflow_state: str = "read",
    declaration_state: str = "read",
    entry_form: str = "directory",
) -> repo_reader.ReadRepoResponse:
    return repo_reader.ReadRepoResponse(
        manifest=repo_reader.ManifestRecord(
            state=repo_reader.ManifestState(manifest_state),
            rows=(repo_reader.RowRecord(key="layout", kind=domain.KIND_APP),),
            note="note",
        ),
        verify=repo_reader.FileRecord(
            state=repo_reader.FileState(verify_state), text="verify body"
        ),
        workflow=repo_reader.FileRecord(
            state=repo_reader.FileState(workflow_state), text="workflow body"
        ),
        top=(
            repo_reader.EntryRecord(
                name="layout", form=repo_reader.EntryForm(entry_form)
            ),
        ),
        examples=(
            repo_reader.EntryRecord(
                name="ports", form=repo_reader.EntryForm(entry_form)
            ),
        ),
        declarations=(
            repo_reader.DeclarationRecord(
                path="layout/.tesser-root",
                state=repo_reader.FileState(declaration_state),
                text="app\n",
            ),
        ),
        requirements=("layout",),
    )


def test_every_manifest_state_maps_to_its_domain_constant() -> None:
    states = (
        repo_reader.ManifestState.READ,
        repo_reader.ManifestState.MISSING,
        repo_reader.ManifestState.UNREADABLE,
        repo_reader.ManifestState.MALFORMED,
        repo_reader.ManifestState.MISSHAPEN,
    )
    mapped = tuple(
        mapping.MapToRepoSpec(_read(manifest_state=state.value)).manifest[0]
        for state in states
    )
    assert mapped == (
        domain.READ,
        domain.MISSING,
        domain.UNREADABLE,
        domain.MALFORMED,
        domain.MISSHAPEN,
    )


def test_every_verify_file_state_maps_to_its_domain_constant() -> None:
    states = (
        repo_reader.FileState.READ,
        repo_reader.FileState.MISSING,
        repo_reader.FileState.UNREADABLE,
    )
    mapped = tuple(
        mapping.MapToRepoSpec(_read(verify_state=state.value)).verify[0] for state in states
    )
    assert mapped == (domain.READ, domain.MISSING, domain.UNREADABLE)


def test_every_workflow_file_state_maps_to_its_domain_constant() -> None:
    states = (
        repo_reader.FileState.READ,
        repo_reader.FileState.MISSING,
        repo_reader.FileState.UNREADABLE,
    )
    mapped = tuple(
        mapping.MapToRepoSpec(_read(workflow_state=state.value)).workflow[0]
        for state in states
    )
    assert mapped == (domain.READ, domain.MISSING, domain.UNREADABLE)


def test_every_declaration_state_maps_to_its_domain_constant() -> None:
    states = (
        repo_reader.FileState.READ,
        repo_reader.FileState.MISSING,
        repo_reader.FileState.UNREADABLE,
    )
    mapped = tuple(
        mapping.MapToRepoSpec(_read(declaration_state=state.value)).declarations[0][1]
        for state in states
    )
    assert mapped == (domain.READ, domain.MISSING, domain.UNREADABLE)


def test_every_entry_form_maps_to_its_domain_constant() -> None:
    forms = (repo_reader.EntryForm.DIRECTORY, repo_reader.EntryForm.SYMLINK)
    mapped = tuple(
        mapping.MapToRepoSpec(_read(entry_form=form.value)).top[0][1] for form in forms
    )
    assert mapped == (domain.DIRECTORY, domain.SYMLINK)


def test_an_examples_entry_form_maps_to_its_domain_constant() -> None:
    forms = (repo_reader.EntryForm.DIRECTORY, repo_reader.EntryForm.SYMLINK)
    mapped = tuple(
        mapping.MapToRepoSpec(_read(entry_form=form.value)).examples[0][1] for form in forms
    )
    assert mapped == (domain.DIRECTORY, domain.SYMLINK)


def test_the_spec_carries_the_rows_and_note_the_reader_gave() -> None:
    spec = mapping.MapToRepoSpec(_read())
    assert spec.manifest[1] == (("layout", domain.KIND_APP),)
    assert spec.manifest[2] == "note"


def test_the_spec_carries_the_file_text_the_reader_gave() -> None:
    spec = mapping.MapToRepoSpec(_read())
    assert spec.verify[1] == "verify body"
    assert spec.workflow[1] == "workflow body"


def test_the_spec_carries_the_declaration_path_text_and_requirements() -> None:
    spec = mapping.MapToRepoSpec(_read())
    assert spec.declarations == (("layout/.tesser-root", domain.READ, "app\n"),)
    assert spec.requirements == ("layout",)


def test_the_spec_carries_the_entry_names_the_reader_gave() -> None:
    spec = mapping.MapToRepoSpec(_read())
    assert spec.top == (("layout", domain.DIRECTORY),)
    assert spec.examples == (("ports", domain.DIRECTORY),)


def test_the_mapper_is_a_repo_spec_a_repo_builds_from() -> None:
    spec = mapping.MapToRepoSpec(_read())
    built = domain.Repo(spec)
    assert built.trees() == (domain.Text("layout"),)


def test_empty_collections_map_to_empty_tuples() -> None:
    read = repo_reader.ReadRepoResponse(
        manifest=repo_reader.ManifestRecord(
            state=repo_reader.ManifestState.READ, rows=(), note=""
        ),
        verify=repo_reader.FileRecord(state=repo_reader.FileState.READ, text=""),
        workflow=repo_reader.FileRecord(state=repo_reader.FileState.READ, text=""),
        top=(),
        examples=(),
        declarations=(),
        requirements=(),
    )

    spec = mapping.MapToRepoSpec(read)

    assert spec.manifest == (domain.READ, (), "")
    assert (spec.top, spec.examples, spec.declarations, spec.requirements) == ((), (), (), ())
