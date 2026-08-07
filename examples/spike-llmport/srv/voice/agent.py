from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import tesser.srv as ts
from livekit.agents import Agent, ToolError, function_tool

import voicewire


class ToolAgent(Agent, ts.Host):

    def __init__(
        self,
        handler: voicewire.ToolSurface,
        halt: Callable[[], Awaitable[None]],
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

    async def _rebind(self, turn: voicewire.ToolTurn) -> None:
        await self.update_tools(
            [function_tool(self._shim(schema), raw_schema=schema) for schema in turn.tools]
        )

    def _shim(self, schema: dict[str, object]) -> Callable[..., Awaitable[str]]:
        async def call(raw_arguments: dict[str, object]) -> str:
            async with self._lock:
                try:
                    turn = self._handler.dispatch(str(schema["name"]), raw_arguments)
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
                    await self._rebind(turn)
                except Exception:
                    await self._halt()
                    raise
                return turn.reply

        return call
