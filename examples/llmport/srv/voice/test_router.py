from __future__ import annotations

import tesser.testing as ts

import scheduling.adapters.handlers.handlers as handlers
import srv.voice.router as router
import protocol.voice as voice


@ts.fake
class FakeToolEndpoint(voice.ToolEndpoint):

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[voice.ToolCall] = []

    def __call__(self, call: voice.ToolCall, /) -> voice.ToolTurn:
        self.calls.append(call)
        return voice.ToolTurn(reply=self.reply, tools=())


def test_a_named_tool_matches_the_route_that_declares_it() -> None:
    wanted = FakeToolEndpoint("wanted")
    routes = (
        voice.Route(handlers.PROVIDE_NAME, FakeToolEndpoint("other")),
        voice.Route(handlers.CHOOSE_SLOT, wanted),
    )

    matched = router.match(routes, handlers.CHOOSE_SLOT)

    assert matched is not None
    assert matched.endpoint is wanted


def test_an_unrouted_tool_name_matches_nothing() -> None:
    routes = (voice.Route(handlers.PROVIDE_NAME, FakeToolEndpoint("only")),)

    assert router.match(routes, "cancel_booking") is None


def test_a_host_with_no_routes_matches_nothing() -> None:
    assert router.match((), handlers.PROVIDE_NAME) is None


def test_the_first_route_declaring_a_name_wins() -> None:
    first = FakeToolEndpoint("first")
    routes = (
        voice.Route(handlers.PROVIDE_NAME, first),
        voice.Route(handlers.PROVIDE_NAME, FakeToolEndpoint("second")),
    )

    matched = router.match(routes, handlers.PROVIDE_NAME)

    assert matched is not None
    assert matched.endpoint is first


def test_the_matched_route_is_the_endpoint_the_host_calls() -> None:
    endpoint = FakeToolEndpoint("offer the caller the available slots")
    routes = (voice.Route(handlers.PROVIDE_NAME, endpoint),)

    matched = router.match(routes, handlers.PROVIDE_NAME)

    assert matched is not None
    turn = matched.endpoint(voice.ToolCall(handlers.PROVIDE_NAME, {"name": "Ada"}))
    assert turn.reply == "offer the caller the available slots"
    assert [call.name for call in endpoint.calls] == [handlers.PROVIDE_NAME]


def test_every_tool_the_handler_offers_is_routable() -> None:
    declared = {name for names in handlers.TOOLS_FOR_STEP.values() for name in names}
    routes = tuple(voice.Route(name, FakeToolEndpoint(name)) for name in sorted(declared))

    assert all(router.match(routes, name) is not None for name in declared)
    assert router.match(routes, "cancel_booking") is None
