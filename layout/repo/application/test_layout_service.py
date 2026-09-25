from __future__ import annotations

import tesser.testing as ts

import repo.application as application
import repo.application.ports as ports
import repo.client as client
import repo.domain as domain


@ts.helper
def _row_record(key: str = "appone", kind: str = "app") -> ports.RowRecord:
    return ports.RowRecord(key=key, kind=kind)


@ts.helper
def _manifest_record(
    state: ports.ManifestState = ports.ManifestState.READ,
    rows: tuple[ports.RowRecord, ...] = (_row_record(), _row_record(key="scripts", kind="ungated")),
    note: str = "",
) -> ports.ManifestRecord:
    return ports.ManifestRecord(state=state, rows=rows, note=note)


@ts.helper
def _file_record(state: ports.FileState = ports.FileState.READ, text: str = "") -> ports.FileRecord:
    return ports.FileRecord(state=state, text=text)


@ts.helper
def _entry_record(name: str = "appone", form: ports.EntryForm = ports.EntryForm.DIRECTORY) -> ports.EntryRecord:
    return ports.EntryRecord(name=name, form=form)


@ts.helper
def _declaration_record(
    path: str = "appone/.tesser-root",
    state: ports.FileState = ports.FileState.READ,
    text: str = "app\n",
) -> ports.DeclarationRecord:
    return ports.DeclarationRecord(path=path, state=state, text=text)


@ts.helper
def _floor_record(
    path: str = "appone/pyproject.toml",
    key: ports.FloorKey = ports.FloorKey.REQUIRES_PYTHON,
    state: ports.FloorState = ports.FloorState.READ,
    value: str = ">=3.12",
) -> ports.FloorRecord:
    return ports.FloorRecord(path=path, key=key, state=state, value=value)


@ts.helper
def _read_repo_response(
    manifest: ports.ManifestRecord = _manifest_record(),
    verify: ports.FileRecord = _file_record(
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
    workflow: ports.FileRecord = _file_record(
        text=(
            "jobs:\n"
            "  appone:\n"
            "    steps:\n"
            "      - name: gate\n"
            "        run: scripts/verify appone\n"
        ),
    ),
    top: tuple[ports.EntryRecord, ...] = (_entry_record(), _entry_record(name="scripts")),
    examples: tuple[ports.EntryRecord, ...] = (),
    declarations: tuple[ports.DeclarationRecord, ...] = (_declaration_record(),),
    requirements: tuple[str, ...] = ("appone",),
    floors: tuple[ports.FloorRecord, ...] = (_floor_record(),),
) -> ports.ReadRepoResponse:
    return ports.ReadRepoResponse(
        manifest=manifest,
        verify=verify,
        workflow=workflow,
        top=top,
        examples=examples,
        declarations=declarations,
        requirements=requirements,
        floors=floors,
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
        application.MapToRepoSpec(_read_repo_response(manifest=_manifest_record(state=state))).manifest[0]
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
        application.MapToRepoSpec(_read_repo_response(verify=_file_record(state=state))).verify[0]
        for state in states
    )
    assert mapped == (domain.READ, domain.MISSING, domain.UNREADABLE)


def test_every_workflow_file_state_maps_to_its_domain_constant() -> None:
    states = (
        ports.FileState.READ,
        ports.FileState.MISSING,
        ports.FileState.UNREADABLE,
    )
    mapped = tuple(
        application.MapToRepoSpec(_read_repo_response(workflow=_file_record(state=state))).workflow[0]
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
        application.MapToRepoSpec(
            _read_repo_response(declarations=(_declaration_record(state=state),))
        ).declarations[0][1]
        for state in states
    )
    assert mapped == (domain.READ, domain.MISSING, domain.UNREADABLE)


def test_every_entry_form_maps_to_its_domain_constant() -> None:
    forms = (ports.EntryForm.DIRECTORY, ports.EntryForm.SYMLINK)
    mapped = tuple(
        application.MapToRepoSpec(_read_repo_response(top=(_entry_record(form=form),))).top[0][1]
        for form in forms
    )
    assert mapped == (domain.DIRECTORY, domain.SYMLINK)


def test_an_examples_entry_form_maps_to_its_domain_constant() -> None:
    forms = (ports.EntryForm.DIRECTORY, ports.EntryForm.SYMLINK)
    mapped = tuple(
        application.MapToRepoSpec(_read_repo_response(examples=(_entry_record(form=form),))).examples[0][1]
        for form in forms
    )
    assert mapped == (domain.DIRECTORY, domain.SYMLINK)


def test_the_spec_carries_the_rows_and_note_the_reader_gave() -> None:
    repo_spec = application.MapToRepoSpec(
        _read_repo_response(
            manifest=_manifest_record(rows=(_row_record(key="layout", kind=domain.KIND_APP),), note="note")
        )
    )
    assert repo_spec.manifest[1] == (("layout", domain.KIND_APP),)
    assert repo_spec.manifest[2] == "note"


def test_the_spec_carries_the_file_text_the_reader_gave() -> None:
    repo_spec = application.MapToRepoSpec(
        _read_repo_response(verify=_file_record(text="verify body"), workflow=_file_record(text="workflow body"))
    )
    assert repo_spec.verify[1] == "verify body"
    assert repo_spec.workflow[1] == "workflow body"


def test_the_spec_carries_the_declaration_path_text_and_requirements() -> None:
    repo_spec = application.MapToRepoSpec(
        _read_repo_response(
            declarations=(
                _declaration_record(path="layout/.tesser-root", state=ports.FileState.READ, text="app\n"),
            ),
            requirements=("layout",),
        )
    )
    assert repo_spec.declarations == (("layout/.tesser-root", domain.READ, "app\n"),)
    assert repo_spec.requirements == ("layout",)


def test_the_spec_carries_the_entry_names_the_reader_gave() -> None:
    repo_spec = application.MapToRepoSpec(
        _read_repo_response(
            top=(_entry_record(name="layout", form=ports.EntryForm.DIRECTORY),),
            examples=(_entry_record(name="ports", form=ports.EntryForm.DIRECTORY),),
        )
    )
    assert repo_spec.top == (("layout", domain.DIRECTORY),)
    assert repo_spec.examples == (("ports", domain.DIRECTORY),)


def test_the_mapper_is_a_repo_spec_a_repo_builds_from() -> None:
    repo_spec = application.MapToRepoSpec(
        _read_repo_response(
            manifest=_manifest_record(
                state=ports.ManifestState.READ,
                rows=(_row_record(key="layout", kind=domain.KIND_APP),),
            )
        )
    )
    repo = domain.Repo(repo_spec)
    assert repo.trees() == (domain.Text("layout"),)


def test_empty_collections_map_to_empty_tuples() -> None:
    read_repo_response = _read_repo_response(
        manifest=_manifest_record(state=ports.ManifestState.READ, rows=(), note=""),
        top=(),
        examples=(),
        declarations=(),
        requirements=(),
        floors=(),
    )

    repo_spec = application.MapToRepoSpec(read_repo_response)

    assert repo_spec.manifest == (domain.READ, (), "")
    assert (repo_spec.top, repo_spec.examples, repo_spec.declarations, repo_spec.requirements) == ((), (), (), ())
    assert repo_spec.floors == ()


def test_every_floor_key_maps_to_its_domain_constant() -> None:
    keys = (
        ports.FloorKey.REQUIRES_PYTHON,
        ports.FloorKey.TARGET_VERSION,
    )
    mapped = tuple(
        application.MapToRepoSpec(_read_repo_response(floors=(_floor_record(key=key),))).floors[0][1]
        for key in keys
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
        application.MapToRepoSpec(_read_repo_response(floors=(_floor_record(state=state),))).floors[0][2]
        for state in states
    )
    assert mapped == (
        domain.READ,
        domain.UNDECLARED,
        domain.UNREADABLE,
        domain.MALFORMED,
    )


def test_the_spec_carries_the_floor_path_and_value_the_reader_gave() -> None:
    repo_spec = application.MapToRepoSpec(
        _read_repo_response(
            floors=(
                _floor_record(
                    path="layout/pyproject.toml",
                    key=ports.FloorKey.REQUIRES_PYTHON,
                    state=ports.FloorState.READ,
                    value=">=3.12",
                ),
            )
        )
    )
    assert repo_spec.floors == (
        ("layout/pyproject.toml", domain.REQUIRES_PYTHON, domain.READ, ">=3.12"),
    )


@ts.fake
class FakeRepoReader(ports.RepoReader):

    def __init__(self, read_repo_response: ports.ReadRepoResponse) -> None:
        self._read_repo_response = read_repo_response
        self.roots: list[str] = []

    def read_repo(self, read_repo_request: ports.ReadRepoRequest) -> ports.ReadRepoResponse:
        self.roots.append(read_repo_request.repo_root)
        return self._read_repo_response


def test_check_passes_the_root_to_the_port() -> None:
    fake_repo_reader = FakeRepoReader(_read_repo_response())
    application.LayoutService(fake_repo_reader).check_layout(client.CheckLayoutRequest(repo_root="/somewhere"))
    assert fake_repo_reader.roots == ["/somewhere"]


def test_trees_passes_the_root_to_the_port() -> None:
    fake_repo_reader = FakeRepoReader(_read_repo_response())
    application.LayoutService(fake_repo_reader).list_trees(client.ListTreesRequest(repo_root="/elsewhere"))
    assert fake_repo_reader.roots == ["/elsewhere"]


def test_a_clean_read_checks_clean_with_counts() -> None:
    read_repo_response = _read_repo_response(
        manifest=_manifest_record(
            rows=(_row_record(key="appone", kind="app"), _row_record(key="scripts", kind="ungated")),
        )
    )
    check_layout_response = application.LayoutService(FakeRepoReader(read_repo_response)).check_layout(
        client.CheckLayoutRequest(repo_root=".")
    )
    assert check_layout_response.problems == ()
    assert check_layout_response.counts == ("2", "1")


def test_problems_come_back_rendered_as_text() -> None:
    read_repo_response = _read_repo_response(
        manifest=_manifest_record(rows=(_row_record(key="appone", kind="library"),))
    )
    check_layout_response = application.LayoutService(FakeRepoReader(read_repo_response)).check_layout(
        client.CheckLayoutRequest(repo_root=".")
    )
    assert any(
        "manifest.json row 'appone' declares unknown kind 'library'" in problem
        for problem in check_layout_response.problems
    ), check_layout_response.problems


def test_trees_returns_the_app_rows() -> None:
    read_repo_response = _read_repo_response(
        manifest=_manifest_record(
            rows=(_row_record(key="appone", kind="app"), _row_record(key="scripts", kind="ungated")),
        )
    )
    list_trees_response = application.LayoutService(FakeRepoReader(read_repo_response)).list_trees(
        client.ListTreesRequest(repo_root=".")
    )
    assert list_trees_response.trees == ("appone",)


def test_a_malformed_manifest_renders_as_one_problem_and_zero_counts() -> None:
    read_repo_response = _read_repo_response(
        manifest=_manifest_record(state=ports.ManifestState.MALFORMED, note="line 1 column 2")
    )
    check_layout_response = application.LayoutService(FakeRepoReader(read_repo_response)).check_layout(
        client.CheckLayoutRequest(repo_root=".")
    )
    assert check_layout_response.problems == ("manifest.json is unreadable: line 1 column 2",)
    assert check_layout_response.counts == ("0", "0")


def test_trees_degrade_when_the_manifest_cannot_be_read() -> None:
    read_repo_response = _read_repo_response(manifest=_manifest_record(state=ports.ManifestState.MALFORMED))
    list_trees_response = application.LayoutService(FakeRepoReader(read_repo_response)).list_trees(
        client.ListTreesRequest(repo_root=".")
    )
    assert list_trees_response.trees == ()
