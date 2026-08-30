from __future__ import annotations

import asyncio

import pytest
import tesser.testing as ts
import livekit.agents as agents

import protocol.voice as voice
import srv.voice.agent as agent


@ts.helper
def tool_turn(reply: str = "spoken", tool: str = "provide_name") -> voice.ToolTurn:
    return voice.ToolTurn(
        reply=reply,
        tools=(
            voice.Tool(
                name=tool,
                description="record what the caller said",
                parameters={
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                    "additionalProperties": False,
                },
            ),
        ),
    )


@ts.fake
class FakeToolSurface(voice.ToolSurface):

    def __init__(self, opening: voice.ToolTurn, standing: voice.ToolTurn) -> None:
        self._opening = opening
        self._standing = standing
        self.begins = 0
        self.statuses = 0

    def instructions(self) -> str:
        return "help the caller book an appointment"

    def begin(self) -> voice.ToolTurn:
        self.begins += 1
        return self._opening

    def status(self) -> voice.ToolTurn:
        self.statuses += 1
        return self._standing


@ts.fake
class FakeUnreachableToolSurface(voice.ToolSurface):

    def instructions(self) -> str:
        return "help the caller book an appointment"

    def begin(self) -> voice.ToolTurn:
        raise RuntimeError("the context is unreachable")

    def status(self) -> voice.ToolTurn:
        raise RuntimeError("the context is unreachable")


@ts.fake
class FakeEndpoint(voice.ToolEndpoint):

    def __init__(self, answer: voice.ToolTurn) -> None:
        self._answer = answer
        self.calls: list[str] = []

    def __call__(self, call: voice.ToolCall, /) -> voice.ToolTurn:
        self.calls.append(call.text("name"))
        return self._answer


@ts.fake
class FakeRefusingEndpoint(voice.ToolEndpoint):

    def __call__(self, call: voice.ToolCall, /) -> voice.ToolTurn:
        raise voice.BadToolCall("name must be a string")


@ts.fake
class FakeBrokenEndpoint(voice.ToolEndpoint):

    def __call__(self, call: voice.ToolCall, /) -> voice.ToolTurn:
        raise RuntimeError("the context is unreachable")


class TestToolAgent:

    def test_the_agent_speaks_the_instructions_the_surface_owns(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        surface = FakeToolSurface(tool_turn(), tool_turn())
        mounted = agent.ToolAgent(surface, (), halt)

        assert mounted.instructions == "help the caller book an appointment"
        assert surface.begins == 0

    def test_opening_the_session_mounts_the_tools_the_surface_handed_back(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        surface = FakeToolSurface(tool_turn(tool="provide_name"), tool_turn())
        mounted = agent.ToolAgent(surface, (), halt)

        asyncio.run(mounted.on_enter())

        assert [mounted_tool.info.name for mounted_tool in mounted.tools] == ["provide_name"]
        assert surface.begins == 1
        assert halted == []

    def test_a_tool_call_reaches_the_route_of_that_name_and_rebinds_to_its_turn(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        surface = FakeToolSurface(tool_turn(tool="provide_name"), tool_turn())
        endpoint = FakeEndpoint(tool_turn(reply="recorded", tool="choose_slot"))
        mounted = agent.ToolAgent(
            surface, (voice.Route(name="provide_name", endpoint=endpoint),), halt
        )

        async def drive() -> str:
            await mounted.on_enter()
            return await mounted.tools[0]({"name": "Ada"})

        spoken = asyncio.run(drive())

        assert spoken == "recorded"
        assert endpoint.calls == ["Ada"]
        assert [mounted_tool.info.name for mounted_tool in mounted.tools] == ["choose_slot"]
        assert halted == []

    def test_a_tool_the_routes_do_not_name_is_a_tool_error_and_never_halts(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        surface = FakeToolSurface(tool_turn(tool="provide_name"), tool_turn())
        mounted = agent.ToolAgent(surface, (), halt)

        async def drive() -> str:
            await mounted.on_enter()
            return await mounted.tools[0]({"name": "Ada"})

        with pytest.raises(agents.ToolError, match="unknown tool 'provide_name'"):
            asyncio.run(drive())

        assert halted == []

    def test_a_call_the_model_can_correct_rebinds_from_the_surface_and_never_halts(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        surface = FakeToolSurface(
            tool_turn(tool="provide_name"), tool_turn(reply="try again", tool="choose_slot")
        )
        mounted = agent.ToolAgent(
            surface, (voice.Route(name="provide_name", endpoint=FakeRefusingEndpoint()),), halt
        )

        async def drive() -> str:
            await mounted.on_enter()
            return await mounted.tools[0]({"name": "Ada"})

        with pytest.raises(agents.ToolError, match="name must be a string"):
            asyncio.run(drive())

        assert surface.statuses == 1
        assert [mounted_tool.info.name for mounted_tool in mounted.tools] == ["choose_slot"]
        assert halted == []

    def test_a_failure_the_model_cannot_correct_halts_the_session_and_propagates(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        surface = FakeToolSurface(tool_turn(tool="provide_name"), tool_turn())
        mounted = agent.ToolAgent(
            surface, (voice.Route(name="provide_name", endpoint=FakeBrokenEndpoint()),), halt
        )

        async def drive() -> str:
            await mounted.on_enter()
            return await mounted.tools[0]({"name": "Ada"})

        with pytest.raises(RuntimeError, match="the context is unreachable"):
            asyncio.run(drive())

        assert halted == ["halt"]
        assert surface.statuses == 0

    def test_a_surface_that_cannot_open_halts_the_session_and_propagates(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        mounted = agent.ToolAgent(FakeUnreachableToolSurface(), (), halt)

        with pytest.raises(RuntimeError, match="the context is unreachable"):
            asyncio.run(mounted.on_enter())

        assert halted == ["halt"]
        assert mounted.tools == []
