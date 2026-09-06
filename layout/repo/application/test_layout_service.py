from __future__ import annotations

import tesser.testing as ts

import repo.application as application
import repo.application.ports as ports
import repo.client as client
import repo.domain as domain


@ts.helper
def _read(
    manifest_state: str = "read",
    verify_state: str = "read",
    workflow_state: str = "read",
    declaration_state: str = "read",
    entry_form: str = "directory",
    floor_key: str = "requires-python",
    floor_state: str = "read",
) -> ports.ReadRepoResponse:
    return ports.ReadRepoResponse(
        manifest=ports.ManifestRecord(
            state=ports.ManifestState(manifest_state),
            rows=(ports.RowRecord(key="layout", kind=domain.KIND_APP),),
            note="note",
        ),
        verify=ports.FileRecord(
            state=ports.FileState(verify_state), text="verify body"
        ),
        workflow=ports.FileRecord(
            state=ports.FileState(workflow_state), text="workflow body"
        ),
        top=(
            ports.EntryRecord(
                name="layout", form=ports.EntryForm(entry_form)
            ),
        ),
        examples=(
            ports.EntryRecord(
                name="ports", form=ports.EntryForm(entry_form)
            ),
        ),
        declarations=(
            ports.DeclarationRecord(
                path="layout/.tesser-root",
                state=ports.FileState(declaration_state),
                text="app\n",
            ),
        ),
        requirements=("layout",),
        floors=(
            ports.FloorRecord(
                path="layout/pyproject.toml",
                key=ports.FloorKey(floor_key),
                state=ports.FloorState(floor_state),
                value=">=3.12",
            ),
        ),
    )


def test_every_manifest_state_maps_to_its_domain_constant() -> None:
    states = (
        ports.ManifestState.READ,
        ports.ManifestState.MISSING,
        ports.ManifestState.UNREADABLE,
        ports.ManifestState.MALFORMED,
        ports.ManifestState.MISSHAPEN,
    )
    mapped = tuple(
        application.MapToRepoSpec(_read(manifest_state=state.value)).manifest[0]
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
        ports.FileState.READ,
        ports.FileState.MISSING,
        ports.FileState.UNREADABLE,
    )
    mapped = tuple(
        application.MapToRepoSpec(_read(verify_state=state.value)).verify[0] for state in states
    )
    assert mapped == (domain.READ, domain.MISSING, domain.UNREADABLE)


def test_every_workflow_file_state_maps_to_its_domain_constant() -> None:
    states = (
        ports.FileState.READ,
        ports.FileState.MISSING,
        ports.FileState.UNREADABLE,
    )
    mapped = tuple(
        application.MapToRepoSpec(_read(workflow_state=state.value)).workflow[0]
        for state in states
    )
    assert mapped == (domain.READ, domain.MISSING, domain.UNREADABLE)


def test_every_declaration_state_maps_to_its_domain_constant() -> None:
    states = (
        ports.FileState.READ,
        ports.FileState.MISSING,
        ports.FileState.UNREADABLE,
    )
    mapped = tuple(
        application.MapToRepoSpec(_read(declaration_state=state.value)).declarations[0][1]
        for state in states
    )
    assert mapped == (domain.READ, domain.MISSING, domain.UNREADABLE)


def test_every_entry_form_maps_to_its_domain_constant() -> None:
    forms = (ports.EntryForm.DIRECTORY, ports.EntryForm.SYMLINK)
    mapped = tuple(
        application.MapToRepoSpec(_read(entry_form=form.value)).top[0][1] for form in forms
    )
    assert mapped == (domain.DIRECTORY, domain.SYMLINK)


def test_an_examples_entry_form_maps_to_its_domain_constant() -> None:
    forms = (ports.EntryForm.DIRECTORY, ports.EntryForm.SYMLINK)
    mapped = tuple(
        application.MapToRepoSpec(_read(entry_form=form.value)).examples[0][1] for form in forms
    )
    assert mapped == (domain.DIRECTORY, domain.SYMLINK)


def test_the_spec_carries_the_rows_and_note_the_reader_gave() -> None:
    map_to_repo_spec = application.MapToRepoSpec(_read())
    assert map_to_repo_spec.manifest[1] == (("layout", domain.KIND_APP),)
    assert map_to_repo_spec.manifest[2] == "note"


def test_the_spec_carries_the_file_text_the_reader_gave() -> None:
    map_to_repo_spec = application.MapToRepoSpec(_read())
    assert map_to_repo_spec.verify[1] == "verify body"
    assert map_to_repo_spec.workflow[1] == "workflow body"


def test_the_spec_carries_the_declaration_path_text_and_requirements() -> None:
    map_to_repo_spec = application.MapToRepoSpec(_read())
    assert map_to_repo_spec.declarations == (("layout/.tesser-root", domain.READ, "app\n"),)
    assert map_to_repo_spec.requirements == ("layout",)


def test_the_spec_carries_the_entry_names_the_reader_gave() -> None:
    map_to_repo_spec = application.MapToRepoSpec(_read())
    assert map_to_repo_spec.top == (("layout", domain.DIRECTORY),)
    assert map_to_repo_spec.examples == (("ports", domain.DIRECTORY),)


def test_the_mapper_is_a_repo_spec_a_repo_builds_from() -> None:
    map_to_repo_spec = application.MapToRepoSpec(_read())
    repo = domain.Repo(map_to_repo_spec)
    assert repo.trees() == (domain.Text("layout"),)


def test_empty_collections_map_to_empty_tuples() -> None:
    read_repo_response = ports.ReadRepoResponse(
        manifest=ports.ManifestRecord(
            state=ports.ManifestState.READ, rows=(), note=""
        ),
        verify=ports.FileRecord(state=ports.FileState.READ, text=""),
        workflow=ports.FileRecord(state=ports.FileState.READ, text=""),
        top=(),
        examples=(),
        declarations=(),
        requirements=(),
        floors=(),
    )

    map_to_repo_spec = application.MapToRepoSpec(read_repo_response)

    assert map_to_repo_spec.manifest == (domain.READ, (), "")
    assert (map_to_repo_spec.top, map_to_repo_spec.examples, map_to_repo_spec.declarations, map_to_repo_spec.requirements) == ((), (), (), ())
    assert map_to_repo_spec.floors == ()


def test_every_floor_key_maps_to_its_domain_constant() -> None:
    keys = (
        ports.FloorKey.REQUIRES_PYTHON,
        ports.FloorKey.TARGET_VERSION,
    )
    mapped = tuple(
        application.MapToRepoSpec(_read(floor_key=key.value)).floors[0][1] for key in keys
    )
    assert mapped == (domain.REQUIRES_PYTHON, domain.TARGET_VERSION)


def test_every_floor_state_maps_to_its_domain_constant() -> None:
    states = (
        ports.FloorState.READ,
        ports.FloorState.UNDECLARED,
        ports.FloorState.UNREADABLE,
        ports.FloorState.MALFORMED,
    )
    mapped = tuple(
        application.MapToRepoSpec(_read(floor_state=state.value)).floors[0][2]
        for state in states
    )
    assert mapped == (
        domain.READ,
        domain.UNDECLARED,
        domain.UNREADABLE,
        domain.MALFORMED,
    )


def test_the_spec_carries_the_floor_path_and_value_the_reader_gave() -> None:
    map_to_repo_spec = application.MapToRepoSpec(_read())
    assert map_to_repo_spec.floors == (
        ("layout/pyproject.toml", domain.REQUIRES_PYTHON, domain.READ, ">=3.12"),
    )


@ts.fake
class FakeRepoReader(ports.RepoReader):

    def __init__(self, read_repo_response: ports.ReadRepoResponse) -> None:
        self._read_repo_response = read_repo_response
        self.roots: list[str] = []

    def read(self, read_repo_request: ports.ReadRepoRequest) -> ports.ReadRepoResponse:
        self.roots.append(read_repo_request.repo_root)
        return self._read_repo_response


@ts.helper
def _response(
    kind: str = "app",
) -> ports.ReadRepoResponse:
    return ports.ReadRepoResponse(
        manifest=ports.ManifestRecord(
            state=ports.ManifestState.READ,
            rows=(
                ports.RowRecord(key="appone", kind=kind),
                ports.RowRecord(key="scripts", kind="ungated"),
            ),
            note="",
        ),
        verify=ports.FileRecord(
            state=ports.FileState.READ,
            text=(
                "run_appone() {\n"
                "  tessercheck_tree . || return 1\n"
                "}\n"
                "run_tree() {\n"
                '  case "$1" in\n'
                "    appone)   run_appone ;;\n"
                "  esac\n"
                "}\n"
            ),
        ),
        workflow=ports.FileRecord(
            state=ports.FileState.READ,
            text=(
                "jobs:\n"
                "  appone:\n"
                "    steps:\n"
                "      - name: gate\n"
                "        run: scripts/verify appone\n"
            ),
        ),
        top=(
            ports.EntryRecord(name="appone", form=ports.EntryForm.DIRECTORY),
            ports.EntryRecord(name="scripts", form=ports.EntryForm.DIRECTORY),
        ),
        examples=(),
        declarations=(
            ports.DeclarationRecord(
                path="appone/.tesser-root",
                state=ports.FileState.READ,
                text="app\n",
            ),
        ),
        requirements=("appone",),
        floors=(
            ports.FloorRecord(
                path="appone/pyproject.toml",
                key=ports.FloorKey.REQUIRES_PYTHON,
                state=ports.FloorState.READ,
                value=">=3.12",
            ),
        ),
    )


@ts.helper
def _malformed(
    note: str = "boom",
) -> ports.ReadRepoResponse:
    return ports.ReadRepoResponse(
        manifest=ports.ManifestRecord(
            state=ports.ManifestState.MALFORMED, rows=(), note=note
        ),
        verify=ports.FileRecord(state=ports.FileState.MISSING, text=""),
        workflow=ports.FileRecord(state=ports.FileState.MISSING, text=""),
        top=(),
        examples=(),
        declarations=(),
        requirements=(),
        floors=(),
    )


def test_check_passes_the_root_to_the_port() -> None:
    fake_repo_reader = FakeRepoReader(_response())
    application.LayoutService(fake_repo_reader).check(client.CheckRequest(repo_root="/somewhere"))
    assert fake_repo_reader.roots == ["/somewhere"]


def test_trees_passes_the_root_to_the_port() -> None:
    fake_repo_reader = FakeRepoReader(_response())
    application.LayoutService(fake_repo_reader).trees(client.TreesRequest(repo_root="/elsewhere"))
    assert fake_repo_reader.roots == ["/elsewhere"]


def test_a_clean_read_checks_clean_with_counts() -> None:
    check_response = application.LayoutService(FakeRepoReader(_response())).check(
        client.CheckRequest(repo_root=".")
    )
    assert check_response.problems == ()
    assert check_response.counts == ("2", "1")


def test_problems_come_back_rendered_as_text() -> None:
    check_response = application.LayoutService(FakeRepoReader(_response(kind="library"))).check(
        client.CheckRequest(repo_root=".")
    )
    assert any(
        "manifest.json row 'appone' declares unknown kind 'library'" in problem
        for problem in check_response.problems
    ), check_response.problems


def test_trees_returns_the_app_rows() -> None:
    trees_response = application.LayoutService(FakeRepoReader(_response())).trees(
        client.TreesRequest(repo_root=".")
    )
    assert trees_response.trees == ("appone",)


def test_a_malformed_manifest_renders_as_one_problem_and_zero_counts() -> None:
    check_response = application.LayoutService(
        FakeRepoReader(_malformed(note="line 1 column 2"))
    ).check(client.CheckRequest(repo_root="."))
    assert check_response.problems == ("manifest.json is unreadable: line 1 column 2",)
    assert check_response.counts == ("0", "0")


def test_trees_degrade_when_the_manifest_cannot_be_read() -> None:
    trees_response = application.LayoutService(FakeRepoReader(_malformed())).trees(
        client.TreesRequest(repo_root=".")
    )
    assert trees_response.trees == ()
