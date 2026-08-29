from __future__ import annotations

import tesser.component as ts

import alpha.adapters.repositories.memory as memory
import alpha.adapters.repositories.postgres as postgres
import alpha.application.alpha_service as alpha_service
import alpha.application.ports.beta_check as beta_check
import alpha.client.client as client
import alpha.component.config as config
import pgdatabase.database as pgdatabase
import tesser.errors as errors


class Alpha(ts.Component):

    def __init__(self, cfg: config.Config, database: pgdatabase.Database | None, checks: beta_check.BetaCheck) -> None:
        self._widgets: memory.MemoryWidgetRepository | postgres.PostgresWidgetRepository
        if cfg.database is None:
            self._widgets = memory.MemoryWidgetRepository()
        elif database is None:
            raise errors.invalid("missing_database", f"alpha storage {cfg.storage!r} names a database the app did not build")
        else:
            self._widgets = postgres.PostgresWidgetRepository(database)
        self.client: client.Client = alpha_service.AlphaService(self._widgets, checks)

    async def close(self) -> None:
        await self._widgets.close()
