from __future__ import annotations

import tesser.adapters as ts

import catalog.application.ports as ports


class ReservedNamePolicy(ts.Gateway):

    def __init__(self, reserved: tuple[str, ...]) -> None:
        self._reserved = reserved

    def check_name(self, check_name_request: ports.CheckNameRequest) -> ports.CheckNameResponse:
        if check_name_request.name in self._reserved:
            return ports.CheckNameResponse(
                outcome=ports.CheckNameOutcome.RESERVED, reason="name is reserved"
            )
        return ports.CheckNameResponse(outcome=ports.CheckNameOutcome.ALLOWED, reason="")
