from __future__ import annotations

import tesser.component as ts

import catalog.adapters.gateways as gateways
import catalog.adapters.repositories as repositories
import catalog.application as application
import catalog.client as client


class Catalog(ts.Component):

    def __init__(self) -> None:
        self.client: client.CatalogClient = application.CatalogService(
            repositories.MemoryItemRepository(),
            gateways.ReservedNamePolicy(reserved=("admin",)),
        )

    def close(self) -> None:
        return None
