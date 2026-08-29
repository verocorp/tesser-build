from __future__ import annotations

import asyncio

import pytest

import alpha.adapters.repositories.memory as memory
import alpha.application.ports.widget_repository as widget_repository
import tesser.errors as errors


class TestMemoryWidgetStore:

    async def test_a_saved_widget_is_loaded_and_found_in_a_later_transaction(self) -> None:
        widget_store = memory.MemoryWidgetStore()
        async with widget_store.transaction() as widgets:
            saved = await widgets.save_widget(widget_repository.SaveWidgetRequest(name="a", part="p"))
        async with widget_store.transaction() as widgets:
            loaded = await widgets.load_widget(widget_repository.LoadWidgetRequest(name="a"))
            found = await widgets.find_widget(widget_repository.FindWidgetRequest(name="a"))
            missing = await widgets.find_widget(widget_repository.FindWidgetRequest(name="x"))
        assert saved.name == "a"
        assert loaded.part == "p"
        assert found.found is widget_repository.Found.YES
        assert missing.found is widget_repository.Found.NO

    async def test_loading_an_unknown_widget_is_not_found(self) -> None:
        widget_store = memory.MemoryWidgetStore()
        with pytest.raises(errors.DomainError) as caught:
            async with widget_store.transaction() as widgets:
                await widgets.load_widget(widget_repository.LoadWidgetRequest(name="x"))
        assert caught.value.kind is errors.Kind.NOT_FOUND

    async def test_a_transaction_that_raises_restores_the_state_before_it(self) -> None:
        widget_store = memory.MemoryWidgetStore()
        async with widget_store.transaction() as widgets:
            await widgets.save_widget(widget_repository.SaveWidgetRequest(name="a", part="p"))
        with pytest.raises(RuntimeError):
            async with widget_store.transaction() as widgets:
                await widgets.save_widget(widget_repository.SaveWidgetRequest(name="a", part="q"))
                await widgets.save_widget(widget_repository.SaveWidgetRequest(name="b", part="r"))
                raise RuntimeError("abort")
        async with widget_store.transaction() as widgets:
            loaded = await widgets.load_widget(widget_repository.LoadWidgetRequest(name="a"))
            missing = await widgets.find_widget(widget_repository.FindWidgetRequest(name="b"))
        assert loaded.part == "p"
        assert missing.found is widget_repository.Found.NO

    async def test_a_second_transaction_waits_for_the_first_so_rollback_never_loses_a_commit(self) -> None:
        widget_store = memory.MemoryWidgetStore()
        first_opened = asyncio.Event()
        release_first = asyncio.Event()

        async def first() -> None:
            with pytest.raises(RuntimeError):
                async with widget_store.transaction() as widgets:
                    first_opened.set()
                    await release_first.wait()
                    await widgets.save_widget(widget_repository.SaveWidgetRequest(name="a", part="rolled-back"))
                    raise RuntimeError("abort")

        async def second() -> None:
            await first_opened.wait()
            release_first.set()
            async with widget_store.transaction() as widgets:
                await widgets.save_widget(widget_repository.SaveWidgetRequest(name="b", part="committed"))

        await asyncio.gather(first(), second())
        async with widget_store.transaction() as widgets:
            committed = await widgets.load_widget(widget_repository.LoadWidgetRequest(name="b"))
            rolled_back = await widgets.find_widget(widget_repository.FindWidgetRequest(name="a"))
        assert committed.part == "committed"
        assert rolled_back.found is widget_repository.Found.NO
