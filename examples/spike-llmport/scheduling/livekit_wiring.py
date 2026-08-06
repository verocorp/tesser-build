from __future__ import annotations

from collections.abc import Awaitable, Callable

from livekit.agents import Agent, ToolError, function_tool

from scheduling.application import BookingService
from scheduling.domain import DomainError, InfraError
from scheduling.llm import llm_visible_message
from scheduling.tools import ToolName


class SchedulingAgent(Agent):

    def __init__(
        self, service: BookingService, halt: Callable[[], Awaitable[None]]
    ) -> None:
        super().__init__(
            instructions=(
                "Help the caller book an appointment."
                " Use the tools to record what they say; never invent slots."
            )
        )
        self._service = service
        self._halt = halt
        self._booking = service.begin()

    async def on_enter(self) -> None:
        await self._rebind()

    async def _rebind(self) -> None:
        await self.update_tools(
            [
                function_tool(self._shim(name), raw_schema=schema)
                for name, schema in self._service.llm_tools(self._booking).items()
            ]
        )

    def _shim(self, name: ToolName) -> Callable[..., Awaitable[str]]:
        async def handler(raw_arguments: dict[str, object]) -> str:
            try:
                reply = self._service.execute(self._booking, name, raw_arguments)
            except DomainError as err:
                await self._rebind()
                raise ToolError(llm_visible_message(err)) from err
            except InfraError:
                await self._halt()
                raise
            await self._rebind()
            return reply

        return handler
