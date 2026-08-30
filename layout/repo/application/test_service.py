from __future__ import annotations

import tesser.testing as ts

import repo.application.ports.repo_reader as repo_reader
import repo.application.service as service
import repo.client.client as client


@ts.fake
class FakeRepoReader(repo_reader.RepoReader):

    def __init__(self, response: repo_reader.ReadRepoResponse) -> None:
        self._response = response
        self.roots: list[str] = []

    def read(self, request: repo_reader.ReadRepoRequest) -> repo_reader.ReadRepoResponse:
        self.roots.append(request.repo_root)
        return self._response


@ts.helper
def _response(
    kind: str = "app",
) -> repo_reader.ReadRepoResponse:
    return repo_reader.ReadRepoResponse(
        manifest=repo_reader.ManifestRecord(
            state=repo_reader.ManifestState.READ,
            rows=(
                repo_reader.RowRecord(key="appone", kind=kind),
                repo_reader.RowRecord(key="scripts", kind="ungated"),
            ),
            note="",
        ),
        verify=repo_reader.FileRecord(
            state=repo_reader.FileState.READ,
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
        workflow=repo_reader.FileRecord(
            state=repo_reader.FileState.READ,
            text=(
                "jobs:\n"
                "  appone:\n"
                "    steps:\n"
                "      - name: gate\n"
                "        run: scripts/verify appone\n"
            ),
        ),
        top=(
            repo_reader.EntryRecord(name="appone", form=repo_reader.EntryForm.DIRECTORY),
            repo_reader.EntryRecord(name="scripts", form=repo_reader.EntryForm.DIRECTORY),
        ),
        examples=(),
        declarations=(
            repo_reader.DeclarationRecord(
                path="appone/.tesser-root",
                state=repo_reader.FileState.READ,
                text="app\n",
            ),
        ),
        requirements=("appone",),
        floors=(
            repo_reader.FloorRecord(
                path="appone/pyproject.toml",
                key=repo_reader.FloorKey.REQUIRES_PYTHON,
                state=repo_reader.FloorState.READ,
                value=">=3.12",
            ),
        ),
    )


@ts.helper
def _malformed(
    note: str = "boom",
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
        floors=(),
    )


def test_check_passes_the_root_to_the_port() -> None:
    reader = FakeRepoReader(_response())
    service.LayoutService(reader).check(client.CheckRequest(repo_root="/somewhere"))
    assert reader.roots == ["/somewhere"]


def test_trees_passes_the_root_to_the_port() -> None:
    reader = FakeRepoReader(_response())
    service.LayoutService(reader).trees(client.TreesRequest(repo_root="/elsewhere"))
    assert reader.roots == ["/elsewhere"]


def test_a_clean_read_checks_clean_with_counts() -> None:
    response = service.LayoutService(FakeRepoReader(_response())).check(
        client.CheckRequest(repo_root=".")
    )
    assert response.problems == ()
    assert response.counts == ("2", "1")


def test_problems_come_back_rendered_as_text() -> None:
    response = service.LayoutService(FakeRepoReader(_response(kind="library"))).check(
        client.CheckRequest(repo_root=".")
    )
    assert any(
        "manifest.json row 'appone' declares unknown kind 'library'" in problem
        for problem in response.problems
    ), response.problems


def test_trees_returns_the_app_rows() -> None:
    response = service.LayoutService(FakeRepoReader(_response())).trees(
        client.TreesRequest(repo_root=".")
    )
    assert response.trees == ("appone",)


def test_a_malformed_manifest_renders_as_one_problem_and_zero_counts() -> None:
    response = service.LayoutService(
        FakeRepoReader(_malformed(note="line 1 column 2"))
    ).check(client.CheckRequest(repo_root="."))
    assert response.problems == ("manifest.json is unreadable: line 1 column 2",)
    assert response.counts == ("0", "0")


def test_trees_degrade_when_the_manifest_cannot_be_read() -> None:
    response = service.LayoutService(FakeRepoReader(_malformed())).trees(
        client.TreesRequest(repo_root=".")
    )
    assert response.trees == ()
