from __future__ import annotations

import alpha.adapters.repositories.memory as memory
import alpha.application.ports as ports


class TestMemoryWidgetRepository:

    def test_a_save_answers_the_saved_name(self) -> None:
        memory_widget_repository = memory.MemoryWidgetRepository()
        saved = memory_widget_repository.save(ports.SaveRequest(name="a", standing="kept"))
        assert saved.name == "a"

    def test_a_released_standing_is_taken_and_the_save_still_answers_the_name(self) -> None:
        memory_widget_repository = memory.MemoryWidgetRepository()
        saved = memory_widget_repository.save(ports.SaveRequest(name="a", standing="released"))
        assert saved.name == "a"
