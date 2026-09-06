from __future__ import annotations

import tesser.component as ts

import repo.adapters.repositories as repositories
import repo.application as application
import repo.client as client


class Spec(ts.Spec):

    def __init__(self) -> None:
        return None


class Config(ts.Config):

    def __init__(self, spec: Spec) -> None:
        return None


class Repo(ts.Component):

    def __init__(self, config: Config) -> None:
        self.client: client.RepoClient = application.LayoutService(
            repositories.FilesystemRepoReader()
        )

    def close(self) -> None:
        return None
