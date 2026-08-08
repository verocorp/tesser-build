from __future__ import annotations

import tesser.srv as ts

import scheduling.adapters.handlers as handlers
import protocol.voice as voice


@ts.function
def tools_for(handler: handlers.LlmToolHandler) -> tuple[voice.Route, ...]:
    return (
        voice.Route(handlers.PROVIDE_NAME, handler.provide_name),
        voice.Route(handlers.CHOOSE_SLOT, handler.choose_slot),
        voice.Route(handlers.CONFIRM_BOOKING, handler.confirm),
    )


@ts.function
def match(routes: tuple[voice.Route, ...], name: str) -> voice.Route | None:
    for route in routes:
        if route.name == name:
            return route
    return None
