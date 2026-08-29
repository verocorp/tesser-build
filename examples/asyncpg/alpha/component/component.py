from __future__ import annotations

import tesser.component as ts

import alpha.adapters.repositories.memory as memory
import alpha.adapters.repositories.postgres as postgres
import alpha.application.alpha_service as alpha_service
import alpha.application.ports.beta_check as beta_check
import alpha.application.ports.widget_repository as widget_repository
import alpha.client.client as client
import alpha.component.config as config
import pgdatabase.database as pgdatabase
import tesser.errors as errors


class Alpha(ts.Component):

    def __init__(self, cfg: config.Config, database: pgdatabase.Database | None, checks: beta_check.BetaCheck) -> None:
        widget_store: widget_repository.WidgetStore
        if cfg.database is None:
            widget_store = memory.MemoryWidgetStore()
        elif database is None:
            raise errors.invalid("missing_database", f"alpha storage {cfg.storage!r} names a database the app did not build")
        else:
            widget_store = postgres.PostgresWidgetStore(database)
        self.client: client.Client = alpha_service.AlphaService(widget_store, checks)

    async def close(self) -> None:
        return None
