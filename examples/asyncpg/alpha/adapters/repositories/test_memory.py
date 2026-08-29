from __future__ import annotations

import alpha.adapters.repositories.memory as memory
import alpha.application.ports.widget_repository as widget_repository


class TestMemoryWidgetRepository:

    async def test_a_save_answers_the_saved_name(self) -> None:
        widgets = memory.MemoryWidgetRepository()
        saved = await widgets.save(widget_repository.SaveRequest(name="a"))
        assert saved.name == "a"

    async def test_a_saved_name_is_found_and_an_unsaved_one_is_not(self) -> None:
        widgets = memory.MemoryWidgetRepository()
        await widgets.save(widget_repository.SaveRequest(name="a"))
        found = await widgets.find(widget_repository.FindRequest(name="a"))
        missing = await widgets.find(widget_repository.FindRequest(name="x"))
        assert found.found is widget_repository.Found.YES
        assert missing.found is widget_repository.Found.NO
