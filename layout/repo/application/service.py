from __future__ import annotations

import tesser.application as ts

import repo.application.mapping as mapping
import repo.domain.rules as rules
import repo.application.ports.repo_reader as repo_reader
import repo.client.client as client


class LayoutService(ts.ApplicationService):

    def __init__(self, reader: repo_reader.RepoReader) -> None:
        self._reader = reader

    def check(self, request: client.CheckRequest) -> client.CheckResponse:
        repo_root = rules.RepoRoot(request.repo_root)
        root = str(repo_root)
        read = self._reader.read(repo_reader.ReadRepoRequest(repo_root=root))
        manifest_mapper = mapping.MapToManifestState(manifest_record=read.manifest)
        manifest_rows = tuple((row.key, row.kind) for row in manifest_mapper.rows)
        manifest = (manifest_mapper.state, manifest_rows, manifest_mapper.note)
        verify_mapper = mapping.MapToFileState(file_record=read.verify)
        verify = (verify_mapper.state, verify_mapper.text)
        workflow_mapper = mapping.MapToFileState(file_record=read.workflow)
        workflow = (workflow_mapper.state, workflow_mapper.text)
        top_mappers = tuple(
            mapping.MapToEntryForm(entry_record=entry) for entry in read.top
        )
        top = tuple(
            (entry_mapper.name, entry_mapper.form) for entry_mapper in top_mappers
        )
        example_mappers = tuple(
            mapping.MapToEntryForm(entry_record=entry) for entry in read.examples
        )
        examples = tuple(
            (entry_mapper.name, entry_mapper.form) for entry_mapper in example_mappers
        )
        declaration_mappers = tuple(
            mapping.MapToDeclarationState(declaration_record=record)
            for record in read.declarations
        )
        declarations = tuple(
            (declaration_mapper.path, declaration_mapper.state, declaration_mapper.text)
            for declaration_mapper in declaration_mappers
        )
        spec = rules.RepoSpec(
            manifest=manifest,
            verify=verify,
            workflow=workflow,
            top=top,
            examples=examples,
            declarations=declarations,
            requirements=read.requirements,
        )
        built = rules.Repo(spec)
        problems: list[str] = []
        for problem in built.problems():
            text = problem.text()
            rendered = str(text)
            problems.append(rendered)
        counts: list[str] = []
        for count in built.counts():
            counted = str(count)
            counts.append(counted)
        rendered_problems = tuple(problems)
        rendered_counts = tuple(counts)
        return client.CheckResponse(
            problems=rendered_problems, counts=rendered_counts
        )

    def trees(self, request: client.TreesRequest) -> client.TreesResponse:
        repo_root = rules.RepoRoot(request.repo_root)
        root = str(repo_root)
        read = self._reader.read(repo_reader.ReadRepoRequest(repo_root=root))
        manifest_mapper = mapping.MapToManifestState(manifest_record=read.manifest)
        manifest_rows = tuple((row.key, row.kind) for row in manifest_mapper.rows)
        manifest = (manifest_mapper.state, manifest_rows, manifest_mapper.note)
        verify_mapper = mapping.MapToFileState(file_record=read.verify)
        verify = (verify_mapper.state, verify_mapper.text)
        workflow_mapper = mapping.MapToFileState(file_record=read.workflow)
        workflow = (workflow_mapper.state, workflow_mapper.text)
        top_mappers = tuple(
            mapping.MapToEntryForm(entry_record=entry) for entry in read.top
        )
        top = tuple(
            (entry_mapper.name, entry_mapper.form) for entry_mapper in top_mappers
        )
        example_mappers = tuple(
            mapping.MapToEntryForm(entry_record=entry) for entry in read.examples
        )
        examples = tuple(
            (entry_mapper.name, entry_mapper.form) for entry_mapper in example_mappers
        )
        declaration_mappers = tuple(
            mapping.MapToDeclarationState(declaration_record=record)
            for record in read.declarations
        )
        declarations = tuple(
            (declaration_mapper.path, declaration_mapper.state, declaration_mapper.text)
            for declaration_mapper in declaration_mappers
        )
        spec = rules.RepoSpec(
            manifest=manifest,
            verify=verify,
            workflow=workflow,
            top=top,
            examples=examples,
            declarations=declarations,
            requirements=read.requirements,
        )
        built = rules.Repo(spec)
        listed: list[str] = []
        for tree in built.trees():
            named = str(tree)
            listed.append(named)
        rendered_trees = tuple(listed)
        return client.TreesResponse(trees=rendered_trees)
