from __future__ import annotations

import tesser.srv as ts

import scheduling.adapters.handlers.handlers as handlers
import protocol.voice as voice


@ts.do_not_use_function
def tools_for(handler: handlers.LlmToolHandler) -> tuple[voice.Route, ...]:  # tesser:debt TB051
    return (
        voice.Route(handlers.PROVIDE_NAME, handler.provide_name),
        voice.Route(handlers.CHOOSE_SLOT, handler.choose_slot),
        voice.Route(handlers.CONFIRM_BOOKING, handler.confirm),
    )


@ts.do_not_use_function
def match(routes: tuple[voice.Route, ...], name: str) -> voice.Route | None:  # tesser:debt TB051
    for route in routes:
        if route.name == name:
            return route
    return None
