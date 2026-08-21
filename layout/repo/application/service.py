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
        problems, counts = mapping.report(read)
        return client.CheckResponse(problems=problems, counts=counts)

    def trees(self, request: client.TreesRequest) -> client.TreesResponse:
        repo_root = rules.RepoRoot(request.repo_root)
        root = str(repo_root)
        read = self._reader.read(repo_reader.ReadRepoRequest(repo_root=root))
        listed = mapping.trees(read)
        return client.TreesResponse(trees=listed)
