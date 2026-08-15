from __future__ import annotations

import tesser.application as ts

import repo.application.mapping as mapping
import repo.application.ports.repo_reader as repo_reader
import repo.client.client as client


class LayoutService(ts.ApplicationService):

    def __init__(self, reader: repo_reader.RepoReader) -> None:
        self._reader = reader

    def check(self, request: client.CheckRequest) -> client.CheckResponse:
        read = self._reader.read(repo_reader.ReadRepoRequest(root=request.root))
        return client.CheckResponse(
            problems=mapping.problems(read), counts=mapping.counts(read)
        )

    def trees(self, request: client.TreesRequest) -> client.TreesResponse:
        read = self._reader.read(repo_reader.ReadRepoRequest(root=request.root))
        return client.TreesResponse(trees=mapping.trees(read))
