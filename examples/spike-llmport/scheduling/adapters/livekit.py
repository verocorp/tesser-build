from __future__ import annotations

from collections.abc import Awaitable, Callable

import tesser.adapters as ts
from livekit.agents import Agent, ToolError, function_tool

from scheduling.adapters.handlers import LlmToolHandler
from scheduling.client import BookingStateResponse


class SchedulingAgent(Agent, ts.Handler):

    def __init__(
        self, handler: LlmToolHandler, halt: Callable[[], Awaitable[None]]
    ) -> None:
        super().__init__(
            instructions=(
                "Help the caller book an appointment."
                " Use the tools to record what they say; never invent slots."
            )
        )
        self._handler = handler
        self._halt = halt

    async def on_enter(self) -> None:
        await self._rebind(self._handler.begin())

    async def _rebind(self, state: BookingStateResponse) -> None:
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
