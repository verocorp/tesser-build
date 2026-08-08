from __future__ import annotations

import tesser.srv as ts

import scheduling.adapters.handlers as handlers
import voicewire


@ts.function
def tools_for(handler: handlers.LlmToolHandler) -> tuple[voicewire.Route, ...]:
    return (
        voicewire.Route(handlers.PROVIDE_NAME, handler.provide_name),
        voicewire.Route(handlers.CHOOSE_SLOT, handler.choose_slot),
        voicewire.Route(handlers.CONFIRM_BOOKING, handler.confirm),
    )


@ts.function
def match(routes: tuple[voicewire.Route, ...], name: str) -> voicewire.Route | None:
    for route in routes:
        if route.name == name:
            return route
    return None
