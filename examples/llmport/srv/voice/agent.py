from __future__ import annotations

import asyncio
import collections.abc as abc

import tesser.srv as ts
import livekit.agents as agents

import protocol


class ToolAgent(agents.Agent, ts.Host):

    def __init__(
        self,
        tool_surface: protocol.ToolSurface,
        routes: tuple[protocol.Route, ...],
        tool_halt: protocol.ToolHalt,
    ) -> None:
        super().__init__(instructions=tool_surface.instructions())
        self._tool_surface = tool_surface
        self._routes = routes
        self._tool_halt = tool_halt
        self._lock = asyncio.Lock()

    async def on_enter(self) -> None:
        try:
            await self._rebind(self._tool_surface.begin())  # tesser:debt TB051
        except Exception:
            await self._tool_halt()
            raise

    async def _rebind(self, tool_turn: protocol.ToolTurn) -> None:
        await self.update_tools(
            [agents.function_tool(self._shim(tool.name), raw_schema=tool.schema()) for tool in tool_turn.tools]  # tesser:debt TB051
        )

    def _shim(self, name: str) -> abc.Callable[..., abc.Awaitable[str]]:  # tesser:debt TB022
        async def call(raw_arguments: dict[str, object]) -> str:  # tesser:debt TB023
            async with self._lock:
                route: protocol.Route | None = None
                for candidate in self._routes:
                    if candidate.name == name:
                        route = candidate
                        break
                if route is None:
                    raise agents.ToolError(f"unknown tool {name!r}")
                try:
                    turn = route.endpoint(protocol.ToolCall(name, raw_arguments))
                except (protocol.BadToolCall, ValueError) as err:
                    try:
                        await self._rebind(self._tool_surface.status())  # tesser:debt TB051
                    except Exception:
                        await self._tool_halt()
                        raise
                    raise agents.ToolError(str(err)) from err
                except Exception:
                    await self._tool_halt()
                    raise
                try:
                    await self._rebind(turn)  # tesser:debt TB051
                except Exception:
                    await self._tool_halt()
                    raise
                return turn.reply

        return call
