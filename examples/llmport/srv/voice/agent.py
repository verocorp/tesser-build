from __future__ import annotations

import asyncio
import typing

import tesser.srv as ts
import livekit.agents as livekit_agents

import protocol

_INSTRUCTIONS: typing.Final[str] = (
    "Help the caller book an appointment. Use the tools to record what they say; never invent slots."
)


class ToolAgent(livekit_agents.Agent, ts.Host):

    def __init__(
        self,
        tool_surface: protocol.ToolSurface,
        routes: tuple[protocol.Route, ...],
        tool_halt: protocol.ToolHalt,
    ) -> None:
        super().__init__(instructions=_INSTRUCTIONS)
        self._tool_surface = tool_surface
        self._routes = routes
        self._tool_halt = tool_halt
        self._lock = asyncio.Lock()

    async def on_enter(self) -> None:
        try:
            await self._rebind(self._tool_surface.begin())
        except Exception:
            await self._tool_halt()
            raise

    async def _rebind(self, tool_turn: protocol.ToolTurn) -> None:
        await self.update_tools(
            [livekit_agents.function_tool(ToolInvocation(self, tool.name).call, raw_schema=tool.schema()) for tool in tool_turn.tools]
        )

    async def call_tool(self, name: str, raw_arguments: dict[str, object]) -> str:
        async with self._lock:
            route: protocol.Route | None = None
            for candidate in self._routes:
                if candidate.name == name:
                    route = candidate
                    break
            if route is None:
                raise livekit_agents.ToolError(f"unknown tool {name!r}")
            try:
                turn = route.endpoint(protocol.ToolCall(name, raw_arguments))
            except (protocol.BadToolCall, ValueError) as err:
                try:
                    await self._rebind(self._tool_surface.status())
                except Exception:
                    await self._tool_halt()
                    raise
                raise livekit_agents.ToolError(str(err)) from err
            except Exception:
                await self._tool_halt()
                raise
            try:
                await self._rebind(turn)
            except Exception:
                await self._tool_halt()
                raise
            return turn.reply


class ToolInvocation(ts.Host):

    def __init__(self, tool_agent: ToolAgent, name: str) -> None:
        self._tool_agent = tool_agent
        self._name = name

    async def call(self, raw_arguments: dict[str, object]) -> str:
        return await self._tool_agent.call_tool(self._name, raw_arguments)
