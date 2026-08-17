from __future__ import annotations

import tesser.component as ts

import catalog.adapters.gateways.name_reserved as name_reserved
import catalog.adapters.gateways.repo_memory as repo_memory
import catalog.application.service as service


class Catalog(ts.Component):

    def __init__(self) -> None:
        self.client = service.CatalogService(
            repo_memory.MemoryItemRepository(),
            name_reserved.ReservedNamePolicy(reserved=("admin",)),
        )

    def close(self) -> None:
        return None
