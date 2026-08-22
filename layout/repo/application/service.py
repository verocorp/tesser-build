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
        manifest_state = mapping._manifest_state(read.manifest.state)
        manifest_rows = tuple((row.key, row.kind) for row in read.manifest.rows)
        manifest = (manifest_state, manifest_rows, read.manifest.note)
        verify = (mapping._state(read.verify.state), read.verify.text)
        workflow = (mapping._state(read.workflow.state), read.workflow.text)
        top = tuple((entry.name, mapping._form(entry.form)) for entry in read.top)
        examples = tuple(
            (entry.name, mapping._form(entry.form)) for entry in read.examples
        )
        declarations = tuple(
            (record.path, mapping._state(record.state), record.text)
            for record in read.declarations
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
        manifest_state = mapping._manifest_state(read.manifest.state)
        manifest_rows = tuple((row.key, row.kind) for row in read.manifest.rows)
        manifest = (manifest_state, manifest_rows, read.manifest.note)
        verify = (mapping._state(read.verify.state), read.verify.text)
        workflow = (mapping._state(read.workflow.state), read.workflow.text)
        top = tuple((entry.name, mapping._form(entry.form)) for entry in read.top)
        examples = tuple(
            (entry.name, mapping._form(entry.form)) for entry in read.examples
        )
        declarations = tuple(
            (record.path, mapping._state(record.state), record.text)
            for record in read.declarations
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
