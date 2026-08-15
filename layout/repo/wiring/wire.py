from __future__ import annotations

import tesser.context as ts

import repo.adapters.repositories as repositories
import repo.application.service as service
import repo.client.client as client


@ts.function
def build() -> client.Client:
    return service.LayoutService(repositories.FilesystemRepoReader())
