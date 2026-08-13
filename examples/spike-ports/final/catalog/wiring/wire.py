from __future__ import annotations

import tesser.context as ts

import catalog.adapters.gateways.name_reserved as name_reserved
import catalog.adapters.gateways.repo_memory as repo_memory
import catalog.application.service as service


class CatalogWiring(ts.Wiring):

    def __init__(self) -> None:
        self._service = service.CatalogService(
            repo_memory.MemoryItemRepository(),
            name_reserved.ReservedNamePolicy(reserved=("admin",)),
        )

    def client(self) -> service.CatalogService:
        return self._service
