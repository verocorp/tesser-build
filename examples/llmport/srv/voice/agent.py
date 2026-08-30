from __future__ import annotations

import asyncio
import collections.abc as abc

import tesser.srv as ts
import livekit.agents as agents

import protocol.voice as voice


class ToolAgent(agents.Agent, ts.Host):

    def __init__(
        self,
        surface: voice.ToolSurface,
        routes: tuple[voice.Route, ...],
        halt: abc.Callable[[], abc.Awaitable[None]],
    ) -> None:
        super().__init__(instructions=surface.instructions())
        self._surface = surface
        self._routes = routes
        self._halt = halt
        self._lock = asyncio.Lock()

    async def on_enter(self) -> None:
        try:
            await self._rebind(self._surface.begin())  # tesser:debt TB051
        except Exception:
            await self._halt()
            raise

    async def _rebind(self, turn: voice.ToolTurn) -> None:
        await self.update_tools(
            [agents.function_tool(self._shim(tool.name), raw_schema=tool.schema()) for tool in turn.tools]  # tesser:debt TB051
        )

    def _shim(self, name: str) -> abc.Callable[..., abc.Awaitable[str]]:
        async def call(raw_arguments: dict[str, object]) -> str:
            async with self._lock:
                route: voice.Route | None = None
                for candidate in self._routes:
                    if candidate.name == name:
                        route = candidate
                        break
                if route is None:
                    raise agents.ToolError(f"unknown tool {name!r}")
                try:
                    turn = route.endpoint(voice.ToolCall(name, raw_arguments))
                except (voice.BadToolCall, ValueError) as err:
                    try:
                        await self._rebind(self._surface.status())  # tesser:debt TB051
                    except Exception:
                        await self._halt()
                        raise
                    raise agents.ToolError(str(err)) from err
                except Exception:
                    await self._halt()
                    raise
                try:
                    await self._rebind(turn)  # tesser:debt TB051
                except Exception:
                    await self._halt()
                    raise
                return turn.reply

        return call
