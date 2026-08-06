from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import tesser.adapters as ts
from livekit.agents import Agent, ToolError, function_tool

import scheduling.adapters.handlers as handlers
import scheduling.client as client


class SchedulingAgent(Agent, ts.Handler):

    def __init__(
        self, handler: handlers.LlmToolHandler, halt: Callable[[], Awaitable[None]]
    ) -> None:
        super().__init__(instructions=handler.instructions())
        self._handler = handler
        self._halt = halt
        self._lock = asyncio.Lock()

    async def on_enter(self) -> None:
        try:
            await self._rebind(self._handler.begin())
        except Exception:
            await self._halt()
            raise

    async def _rebind(self, state: client.BookingStateResponse) -> None:
        await self.update_tools(
            [
                function_tool(self._shim(schema), raw_schema=schema)
                for schema in self._handler.tools(state)
            ]
        )

    def _shim(self, schema: dict[str, object]) -> Callable[..., Awaitable[str]]:
        async def call(raw_arguments: dict[str, object]) -> str:
            async with self._lock:
                try:
                    state = self._handler.dispatch(str(schema["name"]), raw_arguments)
                except ValueError as err:
                    try:
                        await self._rebind(self._handler.status())
                    except Exception:
                        await self._halt()
                        raise
                    raise ToolError(str(err)) from err
                except Exception:
                    await self._halt()
                    raise
                try:
                    await self._rebind(state)
                except Exception:
                    await self._halt()
                    raise
                return state.reply

        return call
