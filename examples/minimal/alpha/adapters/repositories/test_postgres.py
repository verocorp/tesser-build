from __future__ import annotations

import os
import uuid

import alpha.adapters.repositories as repositories
import alpha.application.ports as ports


class TestPostgresWidgetStore:

    async def test_a_widget_saved_in_one_transaction_is_found_in_the_next(self) -> None:
        name = str(uuid.uuid4())
        postgres_widget_store = repositories.PostgresWidgetStore(os.environ["ALPHA_STORAGE"])
        async with postgres_widget_store.transaction() as widget_repository:
            missing = await widget_repository.find_widget(ports.FindWidgetRequest(name=name))
            await widget_repository.save_widget(ports.SaveWidgetRequest(name=name, standing="kept"))
        async with postgres_widget_store.transaction() as widget_repository:
            found = await widget_repository.find_widget(ports.FindWidgetRequest(name=name))
        assert (missing.outcome, found.outcome) == (ports.FindWidgetOutcome.NO, ports.FindWidgetOutcome.YES)
