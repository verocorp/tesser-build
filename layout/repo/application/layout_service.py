from __future__ import annotations

import typing

import tesser.application as ts

import repo.application.ports as ports
import repo.client as client
import repo.domain as domain


class MapToRepoSpec(ts.Mapper, domain.RepoSpec):

    def __init__(self, read_repo_response: ports.ReadRepoResponse) -> None:
        match read_repo_response.manifest.state:
            case ports.ManifestState.READ:
                manifest_state = domain.READ
            case ports.ManifestState.MISSING:
                manifest_state = domain.MISSING
            case ports.ManifestState.UNREADABLE:
                manifest_state = domain.UNREADABLE
            case ports.ManifestState.MALFORMED:
                manifest_state = domain.MALFORMED
            case ports.ManifestState.MISSHAPEN:
                manifest_state = domain.MISSHAPEN
            case _ as unreachable_manifest:
                typing.assert_never(unreachable_manifest)
        manifest_rows = tuple(
            (row.key, row.kind) for row in read_repo_response.manifest.rows
        )
        file_states: list[str] = []
        for file_record in (read_repo_response.verify, read_repo_response.workflow):
            match file_record.state:
                case ports.FileState.READ:
                    file_states.append(domain.READ)
                case ports.FileState.MISSING:
                    file_states.append(domain.MISSING)
                case ports.FileState.UNREADABLE:
                    file_states.append(domain.UNREADABLE)
                case _ as unreachable_file:
                    typing.assert_never(unreachable_file)
        verify_state, workflow_state = file_states
        declared: list[tuple[str, str, str]] = []
        for declaration_record in read_repo_response.declarations:
            match declaration_record.state:
                case ports.FileState.READ:
                    declaration_state = domain.READ
                case ports.FileState.MISSING:
                    declaration_state = domain.MISSING
                case ports.FileState.UNREADABLE:
                    declaration_state = domain.UNREADABLE
                case _ as unreachable_declaration:
                    typing.assert_never(unreachable_declaration)
            declared.append(
                (declaration_record.path, declaration_state, declaration_record.text)
            )
        listings: list[tuple[tuple[str, str], ...]] = []
        for entry_records in (read_repo_response.top, read_repo_response.examples):
            listed: list[tuple[str, str]] = []
            for entry_record in entry_records:
                match entry_record.form:
                    case ports.EntryForm.DIRECTORY:
                        entry_form = domain.DIRECTORY
                    case ports.EntryForm.SYMLINK:
                        entry_form = domain.SYMLINK
                    case _ as unreachable_entry:
                        typing.assert_never(unreachable_entry)
                listed.append((entry_record.name, entry_form))
            listings.append(tuple(listed))
        top, examples = listings
        stated: list[tuple[str, str, str, str]] = []
        for floor_record in read_repo_response.floors:
            match floor_record.key:
                case ports.FloorKey.REQUIRES_PYTHON:
                    floor_key = domain.REQUIRES_PYTHON
                case ports.FloorKey.TARGET_VERSION:
                    floor_key = domain.TARGET_VERSION
                case _ as unreachable_key:
                    typing.assert_never(unreachable_key)
            match floor_record.state:
                case ports.FloorState.READ:
                    floor_state = domain.READ
                case ports.FloorState.UNDECLARED:
                    floor_state = domain.UNDECLARED
                case ports.FloorState.UNREADABLE:
                    floor_state = domain.UNREADABLE
                case ports.FloorState.MALFORMED:
                    floor_state = domain.MALFORMED
                case _ as unreachable_floor:
                    typing.assert_never(unreachable_floor)
            stated.append(
                (floor_record.path, floor_key, floor_state, floor_record.value)
            )
        super().__init__(
            manifest=(manifest_state, manifest_rows, read_repo_response.manifest.note),
            verify=(verify_state, read_repo_response.verify.text),
            workflow=(workflow_state, read_repo_response.workflow.text),
            top=top,
            examples=examples,
            declarations=tuple(declared),
            requirements=read_repo_response.requirements,
            floors=tuple(stated),
        )


class LayoutService(ts.ApplicationService):

    def __init__(self, repo_reader: ports.RepoReader) -> None:
        self._repo_reader = repo_reader

    def check(self, check_request: client.CheckRequest) -> client.CheckResponse:
        repo_root = domain.RepoRoot(check_request.repo_root)
        root = str(repo_root)
        read_repo_response = self._repo_reader.read(ports.ReadRepoRequest(repo_root=root))
        repo = domain.Repo(MapToRepoSpec(read_repo_response))
        counts: list[str] = []
        for count in repo.counts():
            counted = str(count)
            counts.append(counted)
        rendered_counts = tuple(counts)
        match repo.health():
            case domain.Health.CLEAN:
                return client.CheckResponse(problems=(), counts=rendered_counts)
            case domain.Health.PROBLEMS:
                problems: list[str] = []
                for problem in repo.problems():
                    text = problem.text()
                    rendered = str(text)
                    problems.append(rendered)
                rendered_problems = tuple(problems)
                return client.CheckResponse(problems=rendered_problems, counts=rendered_counts)
            case _ as unreachable:
                typing.assert_never(unreachable)

    def trees(self, trees_request: client.TreesRequest) -> client.TreesResponse:
        repo_root = domain.RepoRoot(trees_request.repo_root)
        root = str(repo_root)
        read_repo_response = self._repo_reader.read(ports.ReadRepoRequest(repo_root=root))
        repo = domain.Repo(MapToRepoSpec(read_repo_response))
        listed: list[str] = []
        for tree in repo.trees():
            named = str(tree)
            listed.append(named)
        rendered_trees = tuple(listed)
        return client.TreesResponse(trees=rendered_trees)
