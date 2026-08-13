from __future__ import annotations

import tesser.context as ts

import catalog.adapters.gateways.repo_memory as repo_memory
import catalog.application.service as service


class CatalogWiring(ts.Wiring):

    def __init__(self) -> None:
        self._service = service.CatalogService(repo_memory.MemoryItemRepository())

    def client(self) -> service.CatalogService:
        return self._service
