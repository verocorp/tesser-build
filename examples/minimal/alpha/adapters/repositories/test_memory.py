from __future__ import annotations

import alpha.adapters.repositories.memory as memory
import alpha.application.ports.widget_repository as widget_repository


class TestMemoryWidgetRepository:

    def test_a_save_answers_the_saved_name(self) -> None:
        widgets = memory.MemoryWidgetRepository()
        saved = widgets.save(widget_repository.SaveRequest(name="a"))
        assert saved.name == "a"
