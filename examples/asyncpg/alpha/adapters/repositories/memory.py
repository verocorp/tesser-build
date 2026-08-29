from __future__ import annotations

import asyncio
import contextlib
import typing

import tesser.adapters as ts

import alpha.application.ports.widget_repository as widget_repository
import tesser.errors as errors


class MemoryWidgetRepository(ts.Repository):

    def __init__(self, part_by_name: dict[str, str]) -> None:
        self._part_by_name = part_by_name

    async def save_widget(self, request: widget_repository.SaveWidgetRequest) -> widget_repository.SaveWidgetResponse:
        self._part_by_name[request.name] = request.part
        return widget_repository.SaveWidgetResponse(name=request.name)

    async def load_widget(self, request: widget_repository.LoadWidgetRequest) -> widget_repository.LoadWidgetResponse:
        if request.name not in self._part_by_name:
            raise errors.not_found("unknown_widget", f"no widget {request.name!r}")
        return widget_repository.LoadWidgetResponse(name=request.name, part=self._part_by_name[request.name])

    async def find_widget(self, request: widget_repository.FindWidgetRequest) -> widget_repository.FindWidgetResponse:
        found = widget_repository.Found.YES if request.name in self._part_by_name else widget_repository.Found.NO
        return widget_repository.FindWidgetResponse(found=found)


class MemoryWidgetStore(ts.Repository):

    def __init__(self) -> None:
        self._part_by_name: dict[str, str] = {}
        self._transacting = asyncio.Lock()

    @contextlib.asynccontextmanager
    async def transaction(self) -> typing.AsyncIterator[widget_repository.WidgetRepository]:
        async with self._transacting:
            part_by_name_before = dict(self._part_by_name)
            try:
                yield MemoryWidgetRepository(self._part_by_name)
            except BaseException:
                self._part_by_name.clear()
                self._part_by_name.update(part_by_name_before)
                raise
