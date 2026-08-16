from __future__ import annotations

import tesser.component as ts

import repo.adapters.repositories.file_repository as file_repository
import repo.application.service as service
import repo.client.client as client
import repo.wiring.config as config


class Repo(ts.Component):

    def __init__(self, cfg: config.Config) -> None:
        self.client: client.Client = service.LayoutService(
            file_repository.FilesystemRepoReader()
        )

    def close(self) -> None:
        return None
