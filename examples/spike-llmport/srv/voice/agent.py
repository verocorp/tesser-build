from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

import tesser.srv as ts
from livekit.agents import Agent, ToolError, function_tool

import srv.voice.router as router
import voicewire


class ToolAgent(Agent, ts.Host):

    def __init__(
        self,
        surface: voicewire.ToolSurface,
        routes: tuple[voicewire.Route, ...],
        halt: Callable[[], Awaitable[None]],
    ) -> None:
        super().__init__(instructions=surface.instructions())
        self._surface = surface
        self._routes = routes
        self._halt = halt
        self._lock = asyncio.Lock()

    async def on_enter(self) -> None:
        try:
            await self._rebind(self._surface.begin())
        except Exception:
            await self._halt()
            raise

    async def _rebind(self, turn: voicewire.ToolTurn) -> None:
        await self.update_tools(
            [function_tool(self._shim(tool.name), raw_schema=tool.schema()) for tool in turn.tools]
        )

    def _shim(self, name: str) -> Callable[..., Awaitable[str]]:
        async def call(raw_arguments: dict[str, object]) -> str:
            async with self._lock:
                route = router.match(self._routes, name)
                if route is None:
                    raise ToolError(f"unknown tool {name!r}")
                try:
                    turn = route.endpoint(raw_arguments)
                except ValueError as err:
                    try:
                        await self._rebind(self._surface.status())
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
