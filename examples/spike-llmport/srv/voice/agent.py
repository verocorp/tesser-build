from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Protocol

import tesser.context as ts
from livekit.agents import Agent, ToolError, function_tool


class ToolState(Protocol):

    reply: str


class ToolHandler(Protocol):

    def instructions(self) -> str: ...

    def begin(self) -> ToolState: ...

    def status(self) -> ToolState: ...

    def tools(self, state: ToolState) -> tuple[dict[str, object], ...]: ...

    def dispatch(
        self, tool: str, raw_arguments: Mapping[str, object]
    ) -> ToolState: ...


class ToolAgent(Agent):

    def __init__(
        self, handler: ToolHandler, halt: Callable[[], Awaitable[None]]
    ) -> None:
        super().__init__(instructions=handler.instructions())
        self._handler = handler
        self._halt = halt

    async def on_enter(self) -> None:
        await self._rebind(self._handler.begin())

    async def _rebind(self, state: ToolState) -> None:
        await self.update_tools(
            [
                function_tool(self._shim(schema), raw_schema=schema)
                for schema in self._handler.tools(state)
            ]
        )

    def _shim(self, schema: dict[str, object]) -> Callable[..., Awaitable[str]]:
        async def call(raw_arguments: dict[str, object]) -> str:
            try:
                state = self._handler.dispatch(str(schema["name"]), raw_arguments)
            except ValueError as err:
                await self._rebind(self._handler.status())
                raise ToolError(str(err)) from err
            except Exception:
                await self._halt()
                raise
            await self._rebind(state)
            return state.reply

        return call
