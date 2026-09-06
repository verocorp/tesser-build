from __future__ import annotations

import asyncio

import pytest
import tesser.testing as ts
import livekit.agents as agents

import protocol
import srv.voice as voice


@ts.helper
def tool_turn(reply: str = "spoken", tool: str = "provide_name") -> protocol.ToolTurn:
    return protocol.ToolTurn(
        reply=reply,
        tools=(
            protocol.Tool(
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
class FakeToolSurface(protocol.ToolSurface):

    def __init__(self, opening: protocol.ToolTurn, standing: protocol.ToolTurn) -> None:
        self._opening = opening
        self._standing = standing
        self.begins = 0
        self.statuses = 0

    def instructions(self) -> str:
        return "help the caller book an appointment"

    def begin(self) -> protocol.ToolTurn:
        self.begins += 1
        return self._opening

    def status(self) -> protocol.ToolTurn:
        self.statuses += 1
        return self._standing


@ts.fake
class FakeUnreachableToolSurface(protocol.ToolSurface):

    def instructions(self) -> str:
        return "help the caller book an appointment"

    def begin(self) -> protocol.ToolTurn:
        raise RuntimeError("the context is unreachable")

    def status(self) -> protocol.ToolTurn:
        raise RuntimeError("the context is unreachable")


@ts.fake
class FakeEndpoint(protocol.ToolEndpoint):

    def __init__(self, tool_turn: protocol.ToolTurn) -> None:
        self._tool_turn = tool_turn
        self.calls: list[str] = []

    def __call__(self, tool_call: protocol.ToolCall, /) -> protocol.ToolTurn:
        self.calls.append(tool_call.text("name"))
        return self._tool_turn


@ts.fake
class FakeRefusingEndpoint(protocol.ToolEndpoint):

    def __call__(self, tool_call: protocol.ToolCall, /) -> protocol.ToolTurn:
        raise protocol.BadToolCall("name must be a string")


@ts.fake
class FakeBrokenEndpoint(protocol.ToolEndpoint):

    def __call__(self, tool_call: protocol.ToolCall, /) -> protocol.ToolTurn:
        raise RuntimeError("the context is unreachable")


class TestToolAgent:

    def test_the_agent_speaks_the_instructions_the_surface_owns(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        fake_tool_surface = FakeToolSurface(tool_turn(), tool_turn())
        tool_agent = voice.ToolAgent(fake_tool_surface, (), halt)

        assert tool_agent.instructions == "help the caller book an appointment"
        assert fake_tool_surface.begins == 0

    def test_opening_the_session_mounts_the_tools_the_surface_handed_back(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        fake_tool_surface = FakeToolSurface(tool_turn(tool="provide_name"), tool_turn())
        tool_agent = voice.ToolAgent(fake_tool_surface, (), halt)

        asyncio.run(tool_agent.on_enter())

        assert [mounted_tool.info.name for mounted_tool in tool_agent.tools] == ["provide_name"]
        assert fake_tool_surface.begins == 1
        assert halted == []

    def test_a_tool_call_reaches_the_route_of_that_name_and_rebinds_to_its_turn(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        fake_tool_surface = FakeToolSurface(tool_turn(tool="provide_name"), tool_turn())
        fake_endpoint = FakeEndpoint(tool_turn(reply="recorded", tool="choose_slot"))
        tool_agent = voice.ToolAgent(
            fake_tool_surface,
            (protocol.Route(name="provide_name", endpoint=fake_endpoint),),
            halt,
        )

        async def drive() -> str:
            await tool_agent.on_enter()
            return await tool_agent.tools[0]({"name": "Ada"})

        spoken = asyncio.run(drive())

        assert spoken == "recorded"
        assert fake_endpoint.calls == ["Ada"]
        assert [mounted_tool.info.name for mounted_tool in tool_agent.tools] == ["choose_slot"]
        assert halted == []

    def test_a_tool_the_routes_do_not_name_is_a_tool_error_and_never_halts(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        fake_tool_surface = FakeToolSurface(tool_turn(tool="provide_name"), tool_turn())
        tool_agent = voice.ToolAgent(fake_tool_surface, (), halt)

        async def drive() -> str:
            await tool_agent.on_enter()
            return await tool_agent.tools[0]({"name": "Ada"})

        with pytest.raises(agents.ToolError, match="unknown tool 'provide_name'"):
            asyncio.run(drive())

        assert halted == []

    def test_a_call_the_model_can_correct_rebinds_from_the_surface_and_never_halts(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        fake_tool_surface = FakeToolSurface(
            tool_turn(tool="provide_name"), tool_turn(reply="try again", tool="choose_slot")
        )
        tool_agent = voice.ToolAgent(
            fake_tool_surface,
            (protocol.Route(name="provide_name", endpoint=FakeRefusingEndpoint()),),
            halt,
        )

        async def drive() -> str:
            await tool_agent.on_enter()
            return await tool_agent.tools[0]({"name": "Ada"})

        with pytest.raises(agents.ToolError, match="name must be a string"):
            asyncio.run(drive())

        assert fake_tool_surface.statuses == 1
        assert [mounted_tool.info.name for mounted_tool in tool_agent.tools] == ["choose_slot"]
        assert halted == []

    def test_a_failure_the_model_cannot_correct_halts_the_session_and_propagates(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        fake_tool_surface = FakeToolSurface(tool_turn(tool="provide_name"), tool_turn())
        tool_agent = voice.ToolAgent(
            fake_tool_surface,
            (protocol.Route(name="provide_name", endpoint=FakeBrokenEndpoint()),),
            halt,
        )

        async def drive() -> str:
            await tool_agent.on_enter()
            return await tool_agent.tools[0]({"name": "Ada"})

        with pytest.raises(RuntimeError, match="the context is unreachable"):
            asyncio.run(drive())

        assert halted == ["halt"]
        assert fake_tool_surface.statuses == 0

    def test_a_surface_that_cannot_open_halts_the_session_and_propagates(self) -> None:
        halted: list[str] = []

        async def halt() -> None:
            halted.append("halt")

        tool_agent = voice.ToolAgent(FakeUnreachableToolSurface(), (), halt)

        with pytest.raises(RuntimeError, match="the context is unreachable"):
            asyncio.run(tool_agent.on_enter())

        assert halted == ["halt"]
        assert tool_agent.tools == []
