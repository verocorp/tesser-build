from __future__ import annotations

import tesser.adapters as ts

import catalog.application.ports.name_policy as name_policy


class ReservedNamePolicy(ts.Gateway):

    def __init__(self, reserved: tuple[str, ...]) -> None:
        self._reserved = reserved

    def check(self, request: name_policy.CheckNameRequest) -> name_policy.CheckNameResponse:
        if request.name in self._reserved:
            return name_policy.CheckNameResponse(
                verdict=name_policy.NameVerdict.RESERVED, reason="name is reserved"
            )
        return name_policy.CheckNameResponse(
            verdict=name_policy.NameVerdict.ALLOWED, reason=""
        )
