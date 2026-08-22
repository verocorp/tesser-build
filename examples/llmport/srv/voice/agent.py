from __future__ import annotations  # tesser:debt TB074

import asyncio
from collections.abc import Awaitable, Callable

import tesser.srv as ts
from livekit.agents import Agent, ToolError, function_tool

import protocol.voice as voice


class ToolAgent(Agent, ts.Host):

    def __init__(
        self,
        surface: voice.ToolSurface,
        routes: tuple[voice.Route, ...],
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

    async def _rebind(self, turn: voice.ToolTurn) -> None:  # tesser:debt TB051
        await self.update_tools(
            [function_tool(self._shim(tool.name), raw_schema=tool.schema()) for tool in turn.tools]
        )

    def _shim(self, name: str) -> Callable[..., Awaitable[str]]:  # tesser:debt TB051
        async def call(raw_arguments: dict[str, object]) -> str:
            async with self._lock:
                route: voice.Route | None = None
                for candidate in self._routes:
                    if candidate.name == name:
                        route = candidate
                        break
                if route is None:
                    raise ToolError(f"unknown tool {name!r}")
                try:
                    turn = route.endpoint(voice.ToolCall(name, raw_arguments))
                except (voice.BadToolCall, ValueError) as err:
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
