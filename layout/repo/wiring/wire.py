from __future__ import annotations

import tesser.context as ts

import repo.adapters.repositories.file_repository as file_repository
import repo.application.service as service
import repo.client.client as client


@ts.function
def build() -> client.Client:
    return service.LayoutService(file_repository.FilesystemRepoReader())
